from django.shortcuts import render
from django.http import JsonResponse
from django.forms.models import model_to_dict

from . import models

# Create your views here.

# API

def api_snapshots(request):
    if request.method == 'GET':
        # get one or more snapshots based on params
        print(request.GET)
        search = request.GET.get('search', None)
        if search:
            # filter by search term
            # match refs by name
            refs = models.BoundaryReference.objects.filter(names__name__istartswith=search)
            # get any snapshot belonging to the matched refs or its immediate parent
            matches = models.BoundarySnapshot.objects.filter(boundary_ref__in=refs) | models.BoundarySnapshot.objects.filter(boundary_ref__parent__in=refs)
            count = len(matches)
        else:
            # no filtering, get all snapshots
            matches = models.BoundarySnapshot.objects.all()
            count = matches.count()
        # paginate (for now just return first 20)
        matches = matches[:20]
        # serialize
        def serialize_snapshot(m):
            boundary_refs = [{'id':p.id, 'names':[n.name for n in p.names.all()]}
                            for p in m.boundary_ref.get_all_parents()]
            return {'event':model_to_dict(m.event),
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
