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

def get_boundary_refs_sql(country, level):
    # if using hardcoded levels need to set to orig.level
    # if using dynamic tree level need to set to current.level+1
    sql = '''
    WITH cte(id, level, source_id)
    AS (
        SELECT "changeManager_boundaryreference".id, 0, "changeManager_boundaryreference".source_id
        FROM "changeManager_boundaryreference" INNER JOIN "changeManager_boundaryreference_names" ON ("changeManager_boundaryreference"."id" = "changeManager_boundaryreference_names"."boundaryreference_id") INNER JOIN "changeManager_boundaryname" ON ("changeManager_boundaryreference_names"."boundaryname_id" = "changeManager_boundaryname"."id") 
        WHERE "changeManager_boundaryname"."name" = %s
        AND level = 0

        UNION ALL

        SELECT orig.id, orig.level, orig.source_id
        FROM changeManager_boundaryReference AS orig
        INNER JOIN cte AS current
        ON current.id = orig.parent_id
    )
    SELECT *
    FROM cte
    WHERE level = %s
    '''
    return sql
    sqlparams = [country,
                level,
                ]
    results = models.BoundaryReference.objects.raw(sql, sqlparams)
    return results


def get_boundary_refs_tree_sql():
    # if using hardcoded levels need to set to orig.level
    # if using dynamic tree level need to set to current.level+1
    sql = '''
    WITH cte(id, level, source_id)
    AS (
        SELECT "changeManager_boundaryreference".id, 0, "changeManager_boundaryreference".source_id
        FROM "changeManager_boundaryreference" INNER JOIN "changeManager_boundaryreference_names" ON ("changeManager_boundaryreference"."id" = "changeManager_boundaryreference_names"."boundaryreference_id") INNER JOIN "changeManager_boundaryname" ON ("changeManager_boundaryreference_names"."boundaryname_id" = "changeManager_boundaryname"."id") 
        WHERE "changeManager_boundaryname"."name" = %s
        AND level = 0

        UNION ALL

        SELECT orig.id, orig.level, orig.source_id
        FROM changeManager_boundaryReference AS orig
        INNER JOIN cte AS current
        ON current.id = orig.parent_id
    )
    '''
    return sql


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
        # get all boundary refs at level = level, with a root parent whose name = country

        # get core recursive sql for boundary refs
        #res = get_boundary_refs(request.GET['country'], int(request.GET['level']))
        #print(res.query)
        #for r in res:
        #    print(r.source.name, r.parent_id, r.id, r.level, r.names.all()[0].name)
        #fdsafas
        country,level = request.GET['country'], int(request.GET['level'])
        refs_sql = get_boundary_refs_sql(country, level)

        # fetch events
        # add sql to fetch events from the boundaryrefs
        # should be ref->source->events
        # TODO: ACTUALLY should be ref->snapshot->event
        sql = '''
        WITH refs AS (SELECT * FROM ({}))
        SELECT DISTINCT "changeManager_event".*
        FROM "changeManager_event"
        INNER JOIN "refs" ON ("refs"."source_id" = "changeManager_event"."source_id")
        '''.format(refs_sql)
        sqlparams = [country,
                    level]
        events = list(models.Event.objects.raw(sql, sqlparams))
        #for ev in events:
        #    print(model_to_dict(ev))
        #fdaadsfsdfs
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
            event.date_dist = abs(date_now-start) #-mid
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

        # get all sources
        # add sql to fetch all sources from the boundaryrefs
        sql = '''
        WITH refs AS (SELECT * FROM ({}))
        SELECT DISTINCT "changeManager_boundarysource".*
        FROM "changeManager_boundarysource"
        INNER JOIN "refs" ON ("refs"."source_id" = "changeManager_boundarysource"."id")
        '''.format(refs_sql)
        sqlparams = [country,
                    level]
        sources = list(models.BoundarySource.objects.raw(sql, sqlparams))
        #for src in sources:
        #    print(model_to_dict(src))
        #fdaadsfsdfs
        sources = sorted(sources, key=lambda s: s.valid_from)
        datasources = [s for s in sources if s.type == 'DataSource']
        mapsources = [s for s in sources if s.type == 'MapSource']
        textsources = [s for s in sources if s.type == 'TextSource']

        # return
        context = {'ticks':ticks, 'events':events, 'countries':countries, 'levels':levels,
                    'datasources':datasources, 'mapsources':mapsources, 'textsources':textsources,
                    'current_country':country, 'current_level':level}
        print(context)
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
    country = params.pop('country', None)
    level = params.pop('level', None)
    level = int(level)
    # filter results
    results = model.objects.filter(**params)
    #print(results.count(), results)
    # post processing
    if distinct:
        results = results.distinct()
    # boundary ref recursive country + level filter
    # NOTE: this is really hacky, but should work for now
    if model_name in ('changeManager.BoundaryReference','changeManager.BoundarySnapshot'):
        # retrieve using custom sql and raw instead
        if country != None:
            # get sql and params from filter() methods
            sql_main, sql_args_main = results.query.sql_with_params()
            # generate recursive sql for country and level
            sql_refs = get_boundary_refs_tree_sql()
            sql_refs_args = [country]
            sql_refs += 'SELECT * FROM cte'
            if level != None:
                sql_refs += ' WHERE level = %s'
                sql_refs_args.append( level )
            # combine filter (main) and raw (refs) queries
            if model_name == 'changeManager.BoundaryReference':
                sql = '''
                WITH refs AS (SELECT * FROM ({}))
                SELECT main.* FROM ({}) AS main
                INNER JOIN refs ON (main.id = refs.id)
                '''.format(sql_refs, sql_main)
            elif model_name == 'changeManager.BoundarySnapshot':
                sql = '''
                WITH refs AS (SELECT * FROM ({}))
                SELECT main.* FROM ({}) AS main
                INNER JOIN refs ON (main.boundary_ref_id = refs.id)
                '''.format(sql_refs, sql_main)
            # combine args
            sql_args = list(sql_refs_args) + list(sql_args_main)
            # execute
            #print(999,sql_args,sql)
            results = model.objects.raw(sql, sql_args)
            #for r in results:
            #    print(model_to_dict(r))
    # serialize to python
    serialized = CustomSerializer().serialize(queryset=results)
    #print(repr(serialized))
    # return
    return JsonResponse(serialized, safe=False, encoder=CustomJSONEncoder)



