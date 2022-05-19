from django.shortcuts import render, redirect
from django.db import transaction
from django.utils import timezone

import json

from changeManager.models import BoundarySource
from .models import MapDigitizer

# Create your views here.

def digitize_map(request, pk):
    source = BoundarySource.objects.get(pk=pk)
    
    #if request.method == 'GET':
    #    # show current state of the map
    #    return render(request, 'digitize_map.html', {'source':source})

    if request.method == 'POST':
        # receive and save digitized map data
        with transaction.atomic():
            # save raw digitizing data
            data = request.POST['data']
            data = json.loads(data)
            print(data)
            digitizer,created = MapDigitizer.objects.get_or_create(source=source)
            digitizer.digitized_data = data
            digitizer.last_digitized = timezone.now()
            digitizer.save()
            # attempt to create snapshots from digitized line data
            #...

        return redirect('source', source.pk)
