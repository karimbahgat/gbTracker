from django.shortcuts import render
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict

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
        context = {}
        return render(request, 'track.html', context)

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


