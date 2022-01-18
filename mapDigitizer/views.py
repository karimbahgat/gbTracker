from django.shortcuts import render

# Create your views here.

def digitize_map(request):
    map_url = request.GET.get('url', None)
    
    if request.method == 'GET':
        # show current state of the map
        context = {'map_url':map_url}
        return render(request, 'digitize_map.html', context)

    elif request.method == 'POST':
        # receive and save digitized map data
        gdgfdgd
