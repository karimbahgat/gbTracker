
from django.http import HttpResponse
from django.shortcuts import render

from changeManager.models import BoundaryReference, BoundarySnapshot

import json

def home(request):
    toprefs = BoundaryReference.objects.filter(parent=None)
    if toprefs:
        countries = set()
        countries_geoj = {'type':'FeatureCollection', 'features':[]}
        for ref in toprefs:
            name = ref.names.first().name
            countries.add(name)
            snap = ref.snapshots.first()
            if snap:
                geom = snap.geom.__geo_interface__
                props = {'name':name}
                feat = {'type':'Feature', 'geometry':geom, 'properties':props}
                countries_geoj['features'].append(feat)
        countries = sorted(countries)
        countries_geoj = json.dumps(countries_geoj)
    else:
        countries = []
        countries_geoj = 'null'
    context = {'countries':countries, 'countries_geojson':countries_geoj}
    return render(request, 'templates/home.html', context=context)
