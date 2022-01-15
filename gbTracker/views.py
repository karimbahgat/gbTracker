
from django.http import HttpResponse
from django.shortcuts import render

from changeManager.models import BoundarySnapshot

def home(request):
    context = {}
    return render(request, 'templates/home.html', context=context)
