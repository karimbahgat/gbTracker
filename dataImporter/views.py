from django.shortcuts import render
from django.db import transaction

from .changeManager import models

# Create your views here.

#def _import_data(parent, features):
#    '''Create snapshots for all features belonging to a particular parent'''
#    fdsfsdf

def import_from_shapefile(request):
    import shapefile
    import tempfile
    
    # stream uploaded zipfile to disk (to avoid memory crash)
    filename,fobj = list(request.FILES.items())[0]
    if not filename.endswith('.zip'):
        raise Exception('Uploaded file must end with .zip, not: {}'.format(filename))
    temp = tempfile.TemporaryFile()
    for chunk in fobj.chunks():
        temp.write(chunk)

    # add to db inside transaction
    with transaction.atomic():

        # create event
        event = models.Event(request.GET['date_start'], request.GET['date_end'])
        event.save()

        # read shapefile from temporary zipfile
        # (name_field is a list of one or more name_field inputs from a form)
        temp.seek(0)
        reader = shapefile.Reader(temp)
        for feat in reader.iterShapeRecords():
            # create name references
            parent = None
            for name_field in request.GET.get_list('name_field'):
                # WARNING: creates multiple references to parent levels
                ref = models.BoundaryReference(parent=parent)
                ref.save()
                name = feat.record[name_field]
                name_obj = models.BoundaryName(boundary_ref=ref, name=name)
                name_obj.save()
                parent = ref

            # create snapshot
            geom = feat.shape.__geo_interface__
            snap = BoundarySnapshot(event=event, boundary_ref=ref, geom=geom, source=filename)
            snap.save()

    # close
    temp.close()
