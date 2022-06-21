from django.shortcuts import render
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.db.models import Min, Max
from django.apps import apps
from django.core import serializers
from django.core.serializers.python import Serializer as PythonSerializer
from django.core.serializers.json import DjangoJSONEncoder

from changeManager import models

import json

import requests
from shapely.geometry import asShape

# Create your views here.

def track(request):
    '''The main view that visually tracks and displays all data
    related to a particular boundary definition and puts it on 
    a timeline. 
    The boundary definition is based on a search query, based on
    a timestamp, and multiple hierarchical inputs, each allowing a 
    name and code, and whether we want the current level or the 
    level below.
    '''
    if request.method == 'GET':
        context = {'names':request.GET['names'].split('|')}
        return render(request, 'track.html', context)

def api_track(request):
    '''Gets the data needed for the track page.
    Groups and orders the data in json format.
    Eg.: 
    {dates:[
        {date:1999, entries:[
            {type:"change",
            info:{}},
            {type:"snapshot",
            source:"source1",
            source_type:"data",
            snapshots:[snapid1,snapid2,snapid3]},
            {type:"snapshot",
            source:"source2",
            source_type:"map",
            snapshots:[snapid4,snapid5,snapid6]}
        ]}
    ]}
    Or maybe not grouped by date, but rather a flat
    list of entries where each has a date entry,
    and then grouping is done dynamically on the 
    frontend. 
    '''
    # quick hacky version
    # only search for children of toplevel country given by name0
    country = request.GET['names'].split('|')[0]

    # org results
    results = {'entries':[]}

    # first change events
    # refs = models.BoundaryReference.objects.filter(parent__names__name=country)
    # for ref in refs:
    #     entry = {'type':ref.source.type, 'source':ref.source.name}
    #     # add info
    #     # ...
    #     results['entries'].append(entry)

    # then snapshot sources
    sources = models.BoundarySource.objects.filter(type__in=('DataSource','MapSource'), boundary_refs__parent__names__name=country, boundary_refs__snapshots__id__isnull=False).distinct()
    for source in sources:
        entry = {'type':source.type, 
                'source':source.name, 
                'source_id':source.pk,
                'source_url':source.url}

        snaps = models.BoundarySnapshot.objects.filter(boundary_ref__source__pk=source.pk, boundary_ref__parent__names__name=country)
        agg = snaps.aggregate(Min('event__date_start'), Max('event__date_end'))
        entry['valid_from'] = agg['event__date_start__min']
        entry['valid_to'] = agg['event__date_end__max']

        ids = snaps.values_list('id')
        ids = [id[0] for id in ids]
        if not ids:
            continue
        entry['snapshots'] = ids
        
        print(entry)
        results['entries'].append(entry)

    # sort all results
    sort_by = lambda entry: entry['valid_from']
    results['entries'] = sorted(results['entries'], key=sort_by, reverse=True)

    # source types
    sources = models.BoundarySource.objects.filter(boundary_refs__parent__names__name=country).distinct()
    results['datasets'] = [model_to_dict(obj) for obj in sources.filter(type='DataSource')]
    results['maps'] = [model_to_dict(obj) for obj in sources.filter(type='MapSource')]
    results['texts'] = [model_to_dict(obj) for obj in sources.filter(type='TextSource')]

    return JsonResponse(results)


def build(request):
    '''Builds and increment boundary changes one step at a time.
    
    Suggested change events are based on:
    - Looking up change events that matches the boundaryref, returning only 
        the first/closest possible date before/after current date. Only include 
        boundaryrefs above some name/code match threshold. 
    - Same, but instead lookup snapshot matches before/after current date. 
        Then compare current snapshot to the prev/next snapshot to suggest change
        events. Eg if before/after are signif diff, then suggest transferchange. 
        If cannot find prev/next boundaryref match then suggest created/dissolved 
        event, then find overlapping snapshots and add transfer events to these. 
        If name diff is above some thresh, add namechange event. 
    '''
    if request.method == 'GET':
        # modify get params to fetch events
        params = request.GET.copy()
        params = {'snapshots__'+key:val 
                for key,val in request.GET.items()
                if not key.endswith('_source')}
        print(params)

        # fetch events
        events = models.Event.objects.filter(**params).distinct()
        print(events)
        from datetime import date
        date_starts = [event.date_start for event in events]
        date_ends = [event.date_end for event in events]

        # calc current date (for now just setting to start of all events)
        # used for ordering the events
        date_now = date.fromisoformat(min(date_starts)).toordinal()

        # calc event date percents and sort
        mindate_num = date.fromisoformat(min(date_starts)).toordinal()
        maxdate_num = date.fromisoformat(max(date_ends)).toordinal()
        for event in events: 
            start = date.fromisoformat(event.date_start).toordinal()
            end = date.fromisoformat(event.date_end).toordinal()
            event.date_start_perc = (start - mindate_num) / (maxdate_num - mindate_num) * 100
            event.date_end_perc = (end - mindate_num) / (maxdate_num - mindate_num) * 100
            event.date_dur_perc = event.date_end_perc - event.date_start_perc
            mid = (start + end) / 2.0
            event.date_dist = abs(date_now-mid)
        key = lambda e: e.date_dist
        events = sorted(events, key=key)

        # calc tick labels
        ticks = []
        numticks = 5
        incr = (maxdate_num - mindate_num) / (numticks-1)
        cur = mindate_num
        while cur <= maxdate_num:
            print(cur)
            perc = (cur - mindate_num) / (maxdate_num - mindate_num) * 100
            ticks.append({'label':date.fromordinal(int(cur)), 'percent':perc})
            cur += incr
        print(ticks)

        # get all countries
        countries = models.BoundaryReference.objects.filter(parent=None).values('names__name').distinct()
        countries = [c['names__name'] for c in countries]

        # get available levels
        levels = [0,1,2] # hardcoded for now

        # get current country and level
        key = [key for key in request.GET.keys()
                if key.startswith('boundary_ref__')][0]
        level = key.count('parent__') # each __parent__ represents one level up
        country = request.GET[key]

        # get all sources
        params = request.GET.copy()
        params = {key.replace('boundary_ref__','boundary_refs__'):val 
                for key,val in request.GET.items()
                if not key.endswith('_source')}
        sources = models.BoundarySource.objects.filter(**params).distinct()
        datasources = [s for s in sources if s.type == 'DataSource']
        mapsources = [s for s in sources if s.type == 'MapSource']
        textsources = [s for s in sources if s.type == 'TextSource']

        # return
        context = {'ticks':ticks, 'events':events, 'countries':countries, 'levels':levels,
                    'datasources':datasources, 'mapsources':mapsources, 'textsources':textsources,
                    'current_country':country, 'current_level':level}
        print(context)
        return render(request, 'build.html', context)



        # initial anchor points (snapshot ids) chosen
        # display original snapshot including prev/next snapshots/changes
        snapshot_ids = request.GET['anchors']
        context = {'boundaries':[]}
        for pk in snapshot_ids.split(','):
            snap = models.BoundarySnapshot.objects.get(pk=pk)
            # get geometry
            geom = snap.geom.__geo_interface__
            # get prev changes
            url = 'http://127.0.0.1:8000' + reverse('api_suggest_previous_changes')
            params = {'geometry':json.dumps(geom),
                    'date':snap.event.date_end,
                    'match_name':snap.boundary_ref.full_name(),
                    'match_thresh':0.5} # minimum 50% name match
            resp = requests.post(url,
                                data=params)
            prev = json.loads(resp.content)
            # get next changes
            #nxt = requests.post(reverse('api_suggest_next_changes'),
            #                    data={'geometry':geoj})
            # add to list
            geoj = {'type':'Feature', 'geometry':geom}
            item = {'object':snap, 'geojson':json.dumps(geoj),
                    'prev':prev} #, 'next':nxt}
            context['boundaries'].append( item )

        return render(request, 'build.html', context)

    elif request.method == 'POST':
        # receiving change data
        # apply and display modified changes including prev/next snapshots/changes
        fdsfs

# API

class CustomJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__geo_interface__'):
            return obj.__geo_interface__
        return super().default(obj)

class CustomSerializer(PythonSerializer):
    internal_use_only = False

    def handle_fk_field(self, obj, field):
        '''Recursively serialize all foreign key fields'''
        fk_obj = getattr(obj, field.name)
        #print('obj',obj,'fk_obj',fk_obj)
        if fk_obj is not None:
            value = CustomSerializer().serialize([fk_obj])[0] # should only be one for foreign keys
        else:
            value = fk_obj # None
        #print('value',value)
        #print('fk obj',obj,'field',repr(field),'value',value)
        self._current[field.name] = value

    def handle_m2m_field(self, obj, field):
        '''Recursively serialize all many2many fields'''
        if field.remote_field.through._meta.auto_created:
            def m2m_value(value):
                return CustomSerializer().serialize([value])[0] # should only be one
            m2m_iter = getattr(obj, '_prefetched_objects_cache', {}).get(
                field.name,
                getattr(obj, field.name).iterator(),
            )
            self._current[field.name] = [m2m_value(related) for related in m2m_iter]


@csrf_exempt
def api_filter(request):
    '''Generic api for fetching any model with any filter kwargs'''
    # parse parameters
    params = request.GET.copy()
    print(params)
    params = {key:params.get(key) for key in params.keys()} # each value is wrapped in a list
    # get model
    model_name = params.pop('model')
    model = apps.get_model(model_name)
    # get non-filter values
    distinct = params.pop('distinct', False)
    # filter results
    results = model.objects.filter(**params)
    print(results.count(), results)
    # post processing
    if distinct:
        results = results.distinct()
    # serialize to python
    serialized = CustomSerializer().serialize(queryset=results)
    #print(repr(serialized))
    # return
    return JsonResponse(serialized, safe=False, encoder=CustomJSONEncoder)

@csrf_exempt
def api_suggest_previous_changes(request):
    '''Suggest previous changes for a single boundary,
    given a name, date, and geometry.'''
    if request.method == 'POST':
        #print('POST',request.POST)
        # get change events stored in database
        # ... 
        # get previous snapshots
        namesearch = request.POST['match_name']
        matchthresh = request.POST.get('match_thresh', None)
        datesearch = '/' + request.POST['date'] # prior to date
        params = {'search':namesearch, 'date':datesearch}
        if matchthresh:
            params['search_thresh'] = matchthresh
        url = 'http://127.0.0.1:8000' + reverse('api_snapshots')
        resp = requests.get(url,
                            params=params)
        results = json.loads(resp.content)['results']
        results  = sorted(results, key=lambda x: x['object']['event']['date_end'], reverse=True)
        # return the first previous snapshot event that can be considered a change
        for prevmatch in results:
            # load geometry
            prevobj = models.BoundarySnapshot.objects.get(pk=prevmatch['object']['id'])
            # compare geometries
            geom = asShape(json.loads(request.POST['geometry'])).simplify(0.01)
            geom2 = asShape(prevobj.geom.__geo_interface__).simplify(0.01)
            isec = geom.intersection(geom2)
            union = geom.union(geom2)
            overlap = isec.area / union.area
            # serialize
            def serialize_snapshot(m):
                return {'id':m.id,
                        'event':model_to_dict(m.event),
                        'full_name':m.boundary_ref.full_name(),
                        'source':m.source,
                        }
            # suggest different types of change
            data = []
            if overlap < 0.999: # should be ca 95%
                change = {'type':'Transfer', 'date':prevobj.event.date_end,
                        'match_score':prevmatch['match_score'],
                        'overlap':overlap * 100,
                        'from_boundary':serialize_snapshot(prevobj)}
                data.append(change)
            # if any change data, this is the first previous change
            if data:
                resp = JsonResponse(data, safe=False)
                return resp


