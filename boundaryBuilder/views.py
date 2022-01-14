from django.shortcuts import render

from changeManager import models

import json

# Create your views here.

def build(request):
    '''Builds and increment boundary changes one step at a time.'''
    if request.method == 'GET':
        # initial anchor points (snapshot ids) chosen
        # display original snapshot including prev/next snapshots/changes
        snapshot_ids = request.GET['anchors']
        context = {'boundaries':[]}
        for pk in snapshot_ids.split(','):
            snap = models.BoundarySnapshot.objects.get(pk=pk)
            # get geometry
            geom = snap.geom.__geo_interface__
            geoj = {'type':'Feature', 'geometry':geom}
            # get changes
            # ...
            # add to list
            item = {'object':snap, 'geojson':json.dumps(geoj)}
            context['boundaries'].append( item )

        return render(request, 'build.html', context)

    elif request.method == 'POST':
        # receiving change data
        # apply and display modified changes including prev/next snapshots/changes
        fdsfs
