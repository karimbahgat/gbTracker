from django.shortcuts import render
from django.db import transaction

from changeManager import models

# Create your views here.

#def _import_data(parent, features):
#    '''Create snapshots for all features belonging to a particular parent'''
#    fdsfsdf

def import_from_shapefile(request):
    if request.method == 'GET':
        return render(request, 'shapefile_import.html')

    elif request.method == 'POST':
        import shapefile
        import tempfile

        print('POST', request.POST)
        
        # stream uploaded zipfile to disk (to avoid memory crash)
        input_name,fobj = list(request.FILES.items())[0]
        filename = fobj.name
        if not filename.endswith('.zip'):
            raise Exception('Uploaded file must end with .zip, not: {}'.format(filename))
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp:
            temppath = temp.name
            for chunk in fobj.chunks():
                temp.write(chunk)

        # add to db inside transaction
        with transaction.atomic():
            # parse date
            def parse_date(dateval):
                '''Can be a year, year-month, or year-month-day'''
                dateparts = dateval.split('-')
                if len(dateparts) == 1:
                    yr = dateparts[0]
                    start = '{}-01-01'.format(yr)
                    end = '{}-12-31'.format(yr)
                elif len(dateparts) == 2:
                    yr,mn = dateparts
                    start = '{}-{}-01'.format(yr,mn)
                    end = '{}-{}-31'.format(yr,mn)
                elif len(dateparts) == 3:
                    start = end = dateval
                else:
                    raise Exception('"{}" is not a valid date'.format(dateval))
                return start,end
            dateval = request.POST['date']
            start,end = parse_date(dateval)

            # create event
            event = models.Event(date_start=start, date_end=end)
            event.save()

            # read shapefile from temporary zipfile
            # (name_field is a list of one or more name_field inputs from a form)
            reader = shapefile.Reader(temppath)
            for feat in reader.iterShapeRecords():
                # create name references
                parent = None
                for name_field in request.POST.getlist('name_field'):
                    # WARNING: creates multiple references to parent levels
                    if not name_field:
                        continue
                    ref = models.BoundaryReference(parent=parent)
                    ref.save()
                    name = feat.record[name_field]
                    name_obj = models.BoundaryName(boundary_ref=ref, name=name)
                    name_obj.save()
                    parent = ref

                # create snapshot
                geom = feat.shape.__geo_interface__
                snap = models.BoundarySnapshot(event=event, boundary_ref=ref, geom=geom, source=filename)
                snap.save()

        # close
        temp.close()
