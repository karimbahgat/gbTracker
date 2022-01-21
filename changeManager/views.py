from django.http.response import HttpResponse
from django.shortcuts import render
from django.http import JsonResponse
from django.forms.models import fields_for_model, model_to_dict

from . import models

import json

# Create your views here.

def boundary_ref(request, pk):
    '''View of a snapshot instance.'''
    ref = models.BoundaryReference.objects.get(pk=pk)
    context = {'boundary_ref':ref}
    return render(request, 'boundaryref.html', context)

def snapshot(request, pk):
    '''View of a snapshot instance.'''
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

def api_snapshot(request, pk):
    if request.method == 'GET':
        snap = models.BoundarySnapshot.objects.get(pk=pk)
        
        # serialize
        def serialize_snapshot(m):
            boundary_refs = [{'id':p.id, 'names':[n.name for n in p.names.all()]}
                            for p in m.boundary_ref.get_all_parents()]
            return {'event':model_to_dict(m.event),
                    'boundary_refs':boundary_refs,
                    'source':m.source,
                    }
        data = serialize_snapshot(snap)

        # return as json
        resp = JsonResponse(data)
        return resp

def api_snapshots(request):
    if request.method == 'GET':
        # get one or more snapshots based on params
        print(request.GET)
        ids = request.GET.get('ids', None)
        search = request.GET.get('search', None)
        datesearch = request.GET.get('date', None)
        if ids:
            ids = [int(x) for x in ids.split(',')]
            matches = models.BoundarySnapshot.objects.filter(pk__in=ids)
            count = matches.count()
        elif search:
            # build hierarchical search terms (lowest to highest)
            terms = [s.strip() for s in search.split(',') if s.strip()]
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
            kwargs = {}
            if datesearch:
                start,end = _parse_date(datesearch)
                if start:
                    kwargs['event__date_end__gte'] = start
                if end:
                    kwargs['event__date_start__lte'] = end
            matches = models.BoundarySnapshot.objects.filter(boundary_ref__in=refs, **kwargs) | models.BoundarySnapshot.objects.filter(boundary_ref__parent__in=refs, **kwargs)
            matches = sorted(matches, key=lambda snap: max([ref_scores.get(par.id,0) for par in snap.boundary_ref.get_all_parents()]), reverse=True)
            count = len(matches)
        else:
            # no name filtering
            if datesearch:
                # filter by date
                start,end = _parse_date(datesearch)
                kwargs = {}
                if start:
                    kwargs['event__date_end__gte'] = start
                if end:
                    kwargs['event__date_start__lte'] = end
                matches = models.BoundarySnapshot.objects.filter(**kwargs)
            else:
                # get all snapshots
                matches = models.BoundarySnapshot.objects.all()
            count = matches.count()
        # paginate (for now just return first X)
        matches = matches[:100]
        # serialize
        def serialize_snapshot(m):
            boundary_refs = [{'id':p.id, 'names':[n.name for n in p.names.all()]}
                            for p in m.boundary_ref.get_all_parents()]
            return {'id':m.id,
                    'event':model_to_dict(m.event),
                    'boundary_refs':boundary_refs,
                    'source':m.source,
                    }
        matches = [serialize_snapshot(m) for m in matches]
        # format results
        data = {'count':count, 'results':matches}
        # return as json
        resp = JsonResponse(data)
        return resp
    
    elif request.method == 'POST':
        # submit a new snapshot
        fdsfsd

    elif request.method == 'PUT':
        # update an individual snapshot
        fdsfds
