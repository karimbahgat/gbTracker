
from django.http import HttpResponse
from django.shortcuts import render

from changeManager.models import BoundarySnapshot

def home(request):
    context = {}
    # get all snapshots
    snapshots = BoundarySnapshot.objects.all()[:100]
    context['snapshots'] = snapshots
    return render(request, 'templates/home.html', context=context)
