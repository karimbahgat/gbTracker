from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.forms.models import fields_for_model, model_to_dict
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from . import models
from . import forms

import json

# Create your views here.

def overview(request):
    if request.method == 'GET':
        context = {'names':request.GET['names'].split('|')}
        return render(request, 'overview.html', context)

def source(request, pk):
    '''View of a source'''
    src = models.BoundarySource.objects.get(pk=pk)
    toplevel_refs = src.boundary_refs.filter(parent=None)
    context = {'source':src, 'toplevel_refs':toplevel_refs}

    print('typ',src,repr(src.type))
    
    if src.type == 'TextSource':
        return render(request, 'source_text.html', context)
        
    elif src.type == 'DataSource':
        import_params = src.importer.import_params
        try: import_params = json.dumps(import_params, indent=4)
        except: pass
        context['import_params'] = import_params
        return render(request, 'source_data.html', context)
        
    elif src.type == 'MapSource':
        levels = src.boundary_refs.all().values_list('level').distinct()
        levels = [lvl[0] for lvl in levels]
        context['levels'] = sorted(levels)
        return render(request, 'source_map.html', context)

def datasource_add(request):
    if request.method == 'GET':
        # create empty form
        form = forms.BoundarySourceForm(initial={'type':'DataSource'})
        context = {'form': form}
        return render(request, 'source_data_add.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            form = forms.BoundarySourceForm(data)
            if form.is_valid():
                form.save()
                source = form.instance
                # save importer
                from dataImporter.models import DataImporter
                import_params = json.loads(data['import_params'])
                importer = DataImporter(source=source, import_params=import_params)
                importer.save()
                return redirect('source', source.pk)
            else:
                return render(request, 'source_data_add.html', {'form':form})

def mapsource_add(request):
    if request.method == 'GET':
        # create empty form
        form = forms.BoundarySourceForm(initial={'type':'MapSource'})
        context = {'form': form}
        return render(request, 'source_map_add.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            form = forms.BoundarySourceForm(data)
            if form.is_valid():
                form.save()
                source = form.instance
                return redirect('source', source.pk)
            else:
                return render(request, 'source_map_add.html', {'form':form})

def textsource_add(request):
    if request.method == 'GET':
        # create empty form
        form = forms.BoundarySourceForm(initial={'type':'TextSource'})
        context = {'form': form}
        return render(request, 'source_text_add.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            form = forms.BoundarySourceForm(data)
            if form.is_valid():
                form.save()
                source = form.instance
                return redirect('source', source.pk)
            else:
                return render(request, 'source_text_add.html', {'form':form})

def datasource_edit(request, pk):
    '''Edit of a data source'''
    src = models.BoundarySource.objects.get(pk=pk)

    if request.method == 'GET':
        # create empty form
        form = forms.BoundarySourceForm(instance=src)
        import_params = src.importer.import_params
        try: import_params = json.dumps(import_params, indent=4)
        except: pass
        context = {'form': form, 'import_params': import_params}
        return render(request, 'source_data_edit.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            form = forms.BoundarySourceForm(data, instance=src)
            if form.is_valid():
                form.save()
                # save importer
                importer = src.importer
                importer.import_params = json.loads(data['import_params'])
                importer.save()
                return redirect('source', src.pk)
            else:
                return render(request, 'source_data_edit.html', {'form':form})

def mapsource_edit(request, pk):
    '''Edit of a map source'''
    src = models.BoundarySource.objects.get(pk=pk)

    if request.method == 'GET':
        # create empty form
        form = forms.BoundarySourceForm(instance=src)
        context = {'form': form}
        return render(request, 'source_map_edit.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            form = forms.BoundarySourceForm(data, instance=src)
            if form.is_valid():
                form.save()
                return redirect('source', src.pk)
            else:
                return render(request, 'source_map_edit.html', {'form':form})

def textsource_edit(request, pk):
    '''Edit of a text source'''
    src = models.BoundarySource.objects.get(pk=pk)

    if request.method == 'GET':
        # create empty form
        form = forms.BoundarySourceForm(instance=src)
        context = {'form': form}
        return render(request, 'source_text_edit.html', context)

    elif request.method == 'POST':
        with transaction.atomic():
            # save form data
            data = request.POST
            form = forms.BoundarySourceForm(data, instance=src)
            if form.is_valid():
                form.save()
                return redirect('source', src.pk)
            else:
                return render(request, 'source_text_edit.html', {'form':form})

def boundary(request, pk):
    '''View of a boundary ref instance.'''
    ref = models.BoundaryReference.objects.get(pk=pk)
    # main snapshot
    snap = ref.snapshots.first()
    if snap:
        geom = snap.geom.__geo_interface__
        main_geoj = {'type':'Feature', 'geometry':geom}
        main_geoj = json.dumps(main_geoj)
    else:
        main_geoj = 'null'
    # hierarchy snapshots
    subrefs = ref.children.all()
    if subrefs:
        hier_geoj = {'type':'FeatureCollection', 'features':[]}
        for subref in subrefs:
            snap = subref.snapshots.first()
            if snap:
                geom = snap.geom.__geo_interface__
                feat = {'type':'Feature', 'geometry':geom}
                hier_geoj['features'].append(feat)
        hier_geoj = json.dumps(hier_geoj)
    else:
        hier_geoj = 'null'
    context = {'boundary_ref':ref, 
                'main_geojson':main_geoj,
                'hier_geojson':hier_geoj,
                }
    return render(request, 'boundaryref.html', context)

'''
def snapshot(request, pk):
    #''View of a snapshot instance.''
    snap = models.BoundarySnapshot.objects.get(pk=pk)
    geom = snap.geom.__geo_interface__
    geoj = {'type':'Feature', 'geometry':geom}

    # find matching snapshots
    ref_matches = _match_boundary_ref(snap.boundary_ref)
    snapshot_matches = models.BoundarySnapshot.objects.filter(boundary_ref__in=ref_matches) | models.BoundarySnapshot.objects.filter(boundary_ref__parent__in=ref_matches)
    from datetime import date
    date_starts = [s.event.date_start for s in snapshot_matches]
    date_ends = [s.event.date_end for s in snapshot_matches]

    mindate_num = date.fromisoformat(min(date_starts)).toordinal()
    maxdate_num = date.fromisoformat(max(date_ends)).toordinal()
    date_start = date.fromisoformat(snap.event.date_start).toordinal()
    date_end = date.fromisoformat(snap.event.date_end).toordinal()
    for s in snapshot_matches: 
        start = date.fromisoformat(s.event.date_start).toordinal()
        end = date.fromisoformat(s.event.date_end).toordinal()
        s.date_start_perc = (start - mindate_num) / (maxdate_num - mindate_num) * 100
        s.date_end_perc = (end - mindate_num) / (maxdate_num - mindate_num) * 100
        s.date_dur_perc = s.date_end_perc - s.date_start_perc
        mid = (start + end) / 2.0
        s.date_dist = min(abs(date_start-mid), abs(date_end-mid))
    key = lambda s: s.date_dist
    snapshot_matches = sorted(snapshot_matches, key=key)

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

    context = {'snapshot':snap, 'geojson':json.dumps(geoj), 
                'snapshot_matches':snapshot_matches,
                'mindate':min(date_starts), 'maxdate':max(date_ends),
                'ticks':ticks}
    return render(request, 'snapshot.html', context)
'''

# API

def _match_boundary_ref(match_ref):
    parents = match_ref.get_all_parents()
    parent_names = [p.names.first().name for p in parents]
    # build hierarchical search terms (lowest to highest)
    terms = [s.strip() for s in parent_names if s.strip()]
    # find all refs matching the lowest term (at any level)
    refs = models.BoundaryReference.objects.filter(names__name__istartswith=terms[0])
    #print(refs.query)
    #print(refs.explain())
    # calc match score by adding parent filters based on additional search terms
    ref_scores = {}
    for ref in refs:
        if len(terms) > 1:
            # hierarchical search terms
            parent_matches = [1]
            for t in terms[1:]:
                _matches = [n.name.lower().startswith(t.lower())
                                for parent in ref.get_all_parents(include_self=False)
                                for n in parent.names.all()]
                has_match = 1 if any(_matches) else 0
                parent_matches.append(has_match)
            max_score = max(len(terms), len(parent_matches))
            score = sum(parent_matches) / max_score
        else:
            # single search term
            score = 1
        ref_scores[ref.id] = score
    # get any snapshot belonging to the matched refs or its immediate parent
    matches = sorted(refs, key=lambda r: max([ref_scores.get(par.id,0) for par in r.get_all_parents()]), reverse=True)
    return matches

def _parse_date(dateval):
    '''Can be a year, year-month, or year-month-day'''
    if '/' in dateval:
        # from and to datestrings
        fromdate,todate = dateval.split('/')
        fromdate,todate = fromdate.strip(),todate.strip()
        if fromdate and todate:
            start1,end1 = _parse_date(fromdate)
            start2,end2 = _parse_date(todate)
            return min(start1,start2), max(end1,end2)
        elif fromdate:
            start,end = _parse_date(fromdate)
            return start,None
        elif todate:
            start,end = _parse_date(todate)
            return None,end
    else:
        # single date string
        dateparts = dateval.split('-')
        if len(dateparts) == 1:
            yr = dateparts[0]
            start = '{}-01-01'.format(yr)
            end = '{}-12-31'.format(yr)
        elif len(dateparts) == 2:
            yr,mn = dateparts
            start = '{}-{}-01'.format(yr,mn)
            end = '{}-{}-31'.format(yr,mn)
        elif len(dateparts) == 3:
            start = end = dateval
        else:
            raise Exception('"{}" is not a valid date'.format(dateval))
        return start,end

def api_snapshots(request):
    if request.method == 'GET':
        ids = request.GET['ids']
        ids = ids.split(',')
        ids = list(map(int, ids))
        snaps = models.BoundarySnapshot.objects.filter(pk__in=ids)
        feats = []
        for snap in snaps:
            geom = snap.geom.__geo_interface__
            names = [n.name for n in snap.boundary_ref.names.all()]
            props = {'names':names}
            feat = {'type': 'Feature', 'properties': props, 'geometry':geom}
            feats.append(feat)
        coll = {'type': 'FeatureCollection', 'features': feats}
        return JsonResponse(coll)

@csrf_exempt
def api_boundary(request, pk):
    if request.method == 'GET':
        ref = models.BoundaryReference.objects.get(pk=pk)
        
        # serialize
        data = ref.serialize()

        # return as json
        resp = JsonResponse(data)
        return resp

@csrf_exempt
def api_boundaries(request):
    if request.method == 'GET':
        # get one or more snapshots based on params
        print(request.GET)
        ids = request.GET.get('ids', None)
        search = request.GET.get('search', None)
        search_thresh = request.GET.get('search_thresh', None)
        datesearch = request.GET.get('date', None)
        if ids:
            ids = [int(x) for x in ids.split(',')]
            refs = models.BoundaryReference.objects.filter(pk__in=ids)
            count = refs.count()
        elif search:
            # build hierarchical search terms (lowest to highest)
            terms = [s.strip() for s in search.split(',') if s.strip()]
            # find all refs matching the lowest term (at any level)
            refs = models.BoundaryReference.objects.filter(names__name__istartswith=terms[0])
            #print(refs.query)
            #print(refs.explain())
            # calc match score by adding parent filters based on additional search terms
            _ref_scores = {}
            for ref in refs:
                if len(terms) > 1:
                    # hierarchical search terms
                    parent_matches = [1]
                    for t in terms[1:]:
                        _matches = [n.name.lower().startswith(t.lower())
                                        for parent in ref.get_all_parents(include_self=False)
                                        for n in parent.names.all()]
                        has_match = 1 if any(_matches) else 0
                        parent_matches.append(has_match)
                    max_score = max(len(terms), len(parent_matches))
                    score = sum(parent_matches) / max_score
                else:
                    # single search term
                    score = 1
                _ref_scores[ref.id] = score
            # get any reference belonging to the matched refs or its immediate parent
            kwargs = {}
            if datesearch:
                start,end = _parse_date(datesearch)
                if start:
                    kwargs['snapshots__event__date_end__gte'] = start
                if end:
                    kwargs['snapshots__event__date_start__lte'] = end
            refs = models.BoundaryReference.objects.filter(pk__in=refs, **kwargs) | models.BoundaryReference.objects.filter(parent__pk__in=refs, **kwargs)
            # calc final ref scores
            ref_scores = {}
            for ref in refs:
                score = max([_ref_scores.get(par.id,0) for par in ref.get_all_parents()])
                ref_scores[ref.id] = score
            # sort
            refs = sorted(refs, key=lambda ref: ref_scores[ref.id], reverse=True)
            # filter by threshold
            if search_thresh:
                refs = [ref for ref in refs
                        if ref_scores[ref.id] >= float(search_thresh)]
            count = len(refs)
        else:
            # no name filtering
            if datesearch:
                # filter by date
                start,end = _parse_date(datesearch)
                kwargs = {}
                if start:
                    kwargs['snapshots__event__date_end__gte'] = start
                if end:
                    kwargs['snapshots__event__date_start__lte'] = end
                refs = models.BoundaryReference.objects.filter(**kwargs)
            else:
                # get all snapshots
                refs = models.BoundaryReference.objects.all()
            count = refs.count()
        # paginate (for now just return first X)
        refs = refs[:100]
        # serialize
        if search:
            results = [{'object':m.serialize(), 'match_score':ref_scores[m.id] * 100,
                        } 
                        for m in refs]
        else:
            results = [{'object':m.serialize()} for m in refs]
        # add min/max dates for which snapshots are available, or none
        for item in results:
            starts = [s['event']['date_start'] for s in item['object']['snapshots']]
            ends = [s['event']['date_end'] for s in item['object']['snapshots']]
            item['date_start'] = min(starts) if starts else None
            item['date_end'] = min(ends) if ends else None
        # format results
        data = {'count':count, 'results':results}
        # return as json
        resp = JsonResponse(data)
        return resp
    
    elif request.method == 'POST':
        # submit a new snapshot
        fdsfsd

    elif request.method == 'PUT':
        # update an individual snapshot
        fdsfds
