import enum
from django.shortcuts import render, redirect
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

import os
import csv
import logging
import traceback

from changeManager import models

# Create your views here.

def datasets(request):
    sources = models.BoundarySource.objects.all()
    context = {'sources':sources}
    return render(request, 'datasets.html', context)

#def _import_data(parent, features):
#    '''Create snapshots for all features belonging to a particular parent'''
#    fdsfsdf

@csrf_exempt
def datasource_import(request, pk):
    source = models.BoundarySource(pk=pk)

    #if request.method == 'GET':
    #    dfafds #return render(request, 'source_import.html')

    #elif request.method == 'POST':

    if True:
        import shapefile
        import tempfile

        # required post args:
        # - date
        # - name_field (str or list)
        # - iso or iso_field: shortcut to lookup name for level 0

        print('POST', request.POST)

        # load import params
        params = source.importer.import_params.copy()
        print('params', params)

        # # load country data
        # iso2_to_3 = {}
        # iso3_to_name = {}
        # name_to_iso3 = {}
        # filedir = os.path.dirname(__file__)
        # with open(os.path.join(filedir, 'scripts/countries_codes_and_coordinates.csv'), encoding='utf8', newline='') as f:
        #     csvreader = csv.DictReader(f)
        #     for row in csvreader:
        #         name = row['Country'].strip().strip('"')
        #         iso2 = row['Alpha-2 code'].strip().strip('"')
        #         iso3 = row['Alpha-3 code'].strip().strip('"')
        #         iso2_to_3[iso2] = iso3
        #         iso3_to_name[iso3] = name
        #         name_to_iso3[name] = iso3

        # # load country
        # iso = request.POST.get('iso', '')
        # iso = iso2_to_3[iso] if len(iso)==2 else iso
        
        # stream any uploaded zipfile to disk (to avoid memory crash)
        temps = []
        for input_name,fobj in request.FILES.items():
            filename = fobj.name
            if not filename.endswith('.zip'):
                raise Exception('Uploaded file must end with .zip, not: {}'.format(filename))
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp:
                temps.append(temp)
                temppath = temp.name
                for chunk in fobj.chunks():
                    temp.write(chunk)

        # add to db inside transaction
        with transaction.atomic():
            # drop any existing data (refs incl cascading snapshots)
            source.boundary_refs.all().delete()

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
            start1,end1 = parse_date(str(params['valid_from']))
            start2,end2 = parse_date(str(params['valid_to']))
            start = min(start1,start2)
            end = max(end1, end2)

            # create event
            event = models.Event(date_start=start, date_end=end)
            event.save()

            # get source
            # source_name = params['source'][0]
            # source = models.BoundarySource.objects.filter(name=source_name).first()
            # if not source:
            #     source_cite = request.POST.get('source_citation', '')
            #     source_note = request.POST.get('source_note', '')
            #     source_url = request.POST.get('source_url', '')
            #     source = models.BoundarySource(type="DataSource",
            #                                     name=source_name,
            #                                     citation=source_cite,
            #                                     note=source_note,
            #                                     url=source_url,
            #                                     )
            #     source.save()

            # nest multiple inputs
            if 'input' not in params:
                raise Exception("metadata file doesn't have correct format")
            input_arg = params.pop('input')
            if isinstance(input_arg, str):
                inputs = [{'path':input_arg}]
            elif isinstance(input_arg, list):
                inputs = input_arg
            else:
                raise Exception("metadata file contains an error (input arg must be either string or list of dicts)")
            # run one or more imports
            error_count = 0
            for sub_params in inputs:
                _params = params.copy()
                _params.update(sub_params)
                _params['input_path'] = _params.pop('path') # rename path arg
                print('')
                print('-'*30)
                print('import args', _params)
                reader,data = parse_data(**_params)
                #try:
                #    reader,data = parse_data(**_params)
                #except Exception as err:
                #    error_count += 1
                #    logging.warning("error importing data for '{}': {}".format(_params['input_path'], traceback.format_exc()))

                # add to db
                print('adding to db')
                common = {'event':event, 'source':source}
                add_to_db(reader, common, data)
            # update last imported
            importer = source.importer
            importer.last_imported = timezone.now()
            importer.save()

        # delete tempfiles
        for temp in temps:
            os.remove(temp.name)

        # redirect
        return redirect('source', pk)

def parse_data(**params):
    # read shapefile from temporary zipfile
    # (name_field is a list of one or more name_field inputs from a form)

    # get shapefile encoding
    reader_opts = {}
    encoding = params.get('encoding', None)
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

    def iter_nested_shapefile_groups(reader, level_defs, level=0, subset=None):
        # iterate through each group, depth first
        data = []
        level_def = level_defs[level]
        group_field = level_def['id_field'] if level > 0 else None # id not required for adm0
        fields = [v for k,v in level_def.items() if k.endswith('_field')]
        for groupval,_subset in iter_shapefile_groups(reader, group_field, subset):
            # override all level 0 with a single iso country lookup
            #if level == 0 and iso:
            #    groupval = iso3_to_name[iso]
            # item
            item = {'id':groupval, 'level':level, 
                    'positions':_subset}
            rec = reader.record(_subset[0], fields=fields)
            item['name'] = level_def['name'] if 'name' in level_def else rec[level_def['name_field']]
            # next
            if level_def != level_defs[-1]:
                # recurse into next group_field
                children = iter_nested_shapefile_groups(reader, level_defs, level+1, _subset)
            else:
                # last group_field/max depth
                children = []
            data.append({'item':item,'children':children})
        return data

    # begin reading shapefile
    import shapefile
    reader = shapefile.Reader(params['input_path'], **reader_opts)
    print(reader)

    # parse nested structure
    print('parsing shapefile nested structure')
    data = iter_nested_shapefile_groups(reader, params['levels'])
    print(data)

    return reader, data

def dissolve(geoms, dissolve_buffer=None):
    from shapely.geometry import shape
    from shapely.ops import cascaded_union
    dissolve_buffer = 1e-7 if dissolve_buffer is None else dissolve_buffer # default dissolve buffer is approx 1cm
    print('dissolving',len(geoms))
    # dissolve into one geometry
    if len(geoms) > 1:
        geoms = [shape(geom) for geom in geoms]
        geoms = [geom.buffer(dissolve_buffer) for geom in geoms] # fill in gaps prior to merging to avoid nasty holes causing geometry invalidity
        dissolved = cascaded_union(geoms)
        dissolved = dissolved.buffer(-dissolve_buffer) # shrink back the buffer after gaps have been filled and merged
        # attempt to fix any remaining invalid result
        if not dissolved.is_valid:
            dissolved = dissolved.buffer(0)
        dissolved_geom = dissolved.__geo_interface__
    else:
        dissolved_geom = geoms[0]['geometry']
    
    return dissolved_geom

def add_to_db(reader, common, entries, parent=None):
    source = common['source']
    event = common['event']
    for entry in entries:
        print(entry['item'])

        groupval = entry['item']['id']
        level = entry['item']['level']
        name = entry['item']['name']
        subset = entry['item']['positions']
        if not name:
            continue
        name_obj,created = models.BoundaryName.objects.get_or_create(name=name)

        if entry['children']:
            # create parent node
            ref = models.BoundaryReference(parent=parent, source=source, level=level)
            ref.save()
            ref.names.add(name_obj)

            # process all children one level deeper
            add_to_db(reader, common, entry['children'], parent=ref)

        else:
            # reached leaf node
            #print('leaf node!')
            # get geometry, dissolve if multiple with same id
            assert len(subset) >= 1
            if len(subset) == 1:
                i = subset[0]
                shape = reader.shape(i)
                geom = shape.__geo_interface__
            elif len(subset) > 1:
                geoms = [reader.shape(i).__geo_interface__
                        for i in subset]
                geom = dissolve(geoms) #, dissolve_buffer)
            # create ref
            ref = models.BoundaryReference(parent=parent, source=source)
            ref.save()
            ref.names.add(name_obj)
            # create snapshot
            snap = models.BoundarySnapshot(event=event, boundary_ref=ref, geom=geom)
            snap.save()
