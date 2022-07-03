
from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Count, Min, Max

from changeManager.models import BoundaryReference, BoundarySnapshot, BoundarySource

import json

def home(request):
    toprefs = BoundaryReference.objects.filter(parent=None)
    if toprefs:
        countrynames = set()
        countries_geoj = {'type':'FeatureCollection', 'features':[]}
        for ref in toprefs:
            name = ref.names.first().name
            countrynames.add(name)
            #snap = ref.snapshots.first()
            #if snap:
            #    geom = snap.geom.__geo_interface__
            #    props = {'name':name}
            #    feat = {'type':'Feature', 'geometry':geom, 'properties':props}
            #    countries_geoj['features'].append(feat)
        countrynames = sorted(countrynames)
        countries = []
        for country in countrynames:
            print(country)
            levels = []
            for lvl in [0,1,2]:
                parent_param = ['parent']*lvl
                filter_param = '__'.join( ['boundary_refs'] + parent_param + ['names','name'] )
                filter_kwargs = {}
                filter_kwargs[filter_param] = country
                sources = BoundarySource.objects.filter(**filter_kwargs).distinct().count()
                agg = BoundarySource.objects.filter(**filter_kwargs).aggregate(mindate=Min('boundary_refs__snapshots__event__date_start'), maxdate=Max('boundary_refs__snapshots__event__date_end'))
                info = {'name':country, 'level':lvl, 'sources':sources}
                info.update(agg)
                #print(info)
                levels.append(info)
            #print(levels)
            countries.append(levels)
        countries_geoj = json.dumps(countries_geoj)
    else:
        countries = []
        countries_geoj = 'null'
    context = {'countries':countries, 'countries_geojson':countries_geoj}
    return render(request, 'templates/home.html', context=context)
