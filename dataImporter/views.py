import enum
from django.shortcuts import render, redirect
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt

import os
import csv

from changeManager import models

# Create your views here.

#def _import_data(parent, features):
#    '''Create snapshots for all features belonging to a particular parent'''
#    fdsfsdf

@csrf_exempt
def import_from_shapefile(request):
    if request.method == 'GET':
        return render(request, 'shapefile_import.html')

    elif request.method == 'POST':
        import shapefile
        import tempfile

        # required post args:
        # - date
        # - name_field (str or list)
        # - iso or iso_field: shortcut to lookup name for level 0

        print('POST', request.POST)

        # load country data
        iso2_to_3 = {}
        iso3_to_name = {}
        name_to_iso3 = {}
        filedir = os.path.dirname(__file__)
        with open(os.path.join(filedir, 'scripts/countries_codes_and_coordinates.csv'), encoding='utf8', newline='') as f:
            csvreader = csv.DictReader(f)
            for row in csvreader:
                name = row['Country'].strip().strip('"')
                iso2 = row['Alpha-2 code'].strip().strip('"')
                iso3 = row['Alpha-3 code'].strip().strip('"')
                iso2_to_3[iso2] = iso3
                iso3_to_name[iso3] = name
                name_to_iso3[name] = iso3

        # load country
        iso = request.POST.get('iso', '')
        iso = iso2_to_3[iso] if len(iso)==2 else iso
        
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

            # get source
            source = request.POST.getlist('source')
            if isinstance(source, list):
                source = '|'.join(source)

            # read shapefile from temporary zipfile
            # (name_field is a list of one or more name_field inputs from a form)

            # get full zipfile path
            zipfile_file = request.POST.get('zipfile_file', None)
            if zipfile_file:
                zipfile_file = zipfile_file.split('.zip')[-1].strip('/')
                temppath = os.path.join(temppath, zipfile_file)

            # get shapefile encoding
            reader_opts = {}
            encoding = request.POST.get('encoding', None)
            if encoding:
                reader_opts['encoding'] = encoding

            # define nested shapefile groups reading
            def iter_shapefile_groups(reader, group_field=None, subset=None):
                if group_field:
                    # return in groups
                    def iterRecords():
                        if subset:
                            # iterate only at subset indices
                            for i in subset:
                                rec = reader.record(i, fields=[group_field])
                                yield rec
                        else:
                            # iterate all records
                            for rec in reader.iterRecords(fields=[group_field]):
                                yield rec
                    # get all values of group_field with oid
                    vals = ((rec[0],rec.oid) for rec in iterRecords())
                    # group oids by group value
                    import itertools
                    key = lambda x: x[0]
                    for groupval,items in itertools.groupby(sorted(vals, key=key), key=key):
                        # yield each group value with list of index positions
                        positions = [oid for _,oid in items]
                        yield groupval, positions
                else:
                    # return only a single group of entire shapefile
                    groupval = ''
                    positions = list(range(len(reader)))
                    yield groupval, positions

            def iter_nested_shapefile_groups(reader, group_fields, level=0, subset=None):
                # iterate through each group, depth first
                data = []
                group_field = group_fields[level]
                for groupval,_subset in iter_shapefile_groups(reader, group_field, subset):
                    # override all level 0 with a single iso country lookup
                    if level == 0 and iso:
                        groupval = iso3_to_name[iso]
                    # item
                    item = (level, group_field, groupval, _subset)
                    if group_field != group_fields[-1]:
                        # recurse into next group_field
                        children = iter_nested_shapefile_groups(reader, group_fields, level+1, _subset)
                    else:
                        # last group_field/max depth
                        children = []
                    data.append({'item':item,'children':children})
                return data

            # begin reading shapefile
            import shapefile
            reader = shapefile.Reader(temppath, **reader_opts)
            print(reader)

            # parse nested structure
            print('parsing shapefile nested structure')
            name_fields = request.POST.getlist('name_field')
            data = iter_nested_shapefile_groups(reader, name_fields)

            # add to db
            print('adding to db')
            def process_entries(entries, parent=None):
                for entry in entries:
                    print(entry['item'][:3])

                    level, group_field, groupval, subset = entry['item']
                    name = groupval
                    if not name:
                        continue
                    name_obj,created = models.BoundaryName.objects.get_or_create(name=name)

                    if entry['children']:
                        # create parent node
                        ref = models.BoundaryReference(parent=parent)
                        ref.save()
                        ref.names.add(name_obj)

                        # process all children one level deeper
                        process_entries(entry['children'], parent=ref)

                    else:
                        # reached leaf node
                        for i in subset:
                            # create ref
                            ref = models.BoundaryReference(parent=parent)
                            ref.save()
                            ref.names.add(name_obj)
                            # create snapshot
                            shape = reader.shape(i)
                            geom = shape.__geo_interface__
                            snap = models.BoundarySnapshot(event=event, boundary_ref=ref, geom=geom, source=source)
                            snap.save()

            process_entries(data)

            '''
            # begin reading shapefile (old)
            reader = shapefile.Reader(temppath, **reader_opts)
            for feat in reader.iterShapeRecords():
                # create name references
                parent = None
                iso = request.POST.get('iso', '')
                iso = iso2_to_3[iso] if len(iso)==2 else iso
                iso_field = request.POST.get('iso_field', None)
                names = request.POST.getlist('name')
                name_fields = request.POST.getlist('name_field')

                #assert len(names) == len(name_fields)
                #assert len(names) > 0

                for level,name_field in enumerate(name_fields): #(name,name_field) in enumerate(zip(names,name_fields)):
                    # WARNING: creates multiple references to parent levels
                    if name_field:
                        name = feat.record[name_field]
                    if not name:
                        if level == 0:
                            # iso and iso_field serve as shortcuts if ADM0 name is not given
                            if not iso and iso_field:
                                iso = feat.record[iso_field]
                                iso = iso2_to_3[iso] if len(iso)==2 else iso
                            name = iso3_to_name[iso]
                    ref = models.BoundaryReference(parent=parent)
                    ref.save()
                    if name:
                        print(level,name)
                        name_obj,created = models.BoundaryName.objects.get_or_create(name=name)
                        ref.names.add(name_obj)
                    parent = ref

                # create snapshot
                geom = feat.shape.__geo_interface__
                snap = models.BoundarySnapshot(event=event, boundary_ref=ref, geom=geom, source=source)
                snap.save()
            '''

        # close
        temp.close()

        # redirect
        return redirect('import_shapefile')
