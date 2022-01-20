'''
Def import_data()
    Args:
•	path_to_shp
•	[output_dir]
•	Iso
•	Iso_field
•	Iso_path
•	Level
•	Level_field
•	Level_path
•	Type
•	Type_field (either a field name, or a conditional dict of level-field pairs)
•	Year
•	Year_field
•	Name_field (either a field name, or a conditional dict of level-field pairs)
•	Source
•	Download
•	License
•	Dissolve_by
•	Keep_fields

The output is a topojson file and a meta file located in the output_dir.
(Our auto script will simply loop each source folder and use the same name in a target root folder)

A meta.txt file contains a json dict of all these args which defines how to import a single data file. 

For importing from a large number of data files where some of the args are defined by the path/file names,
the path arg allows either a list of pathnames or regex style wildcards in order to loop through folder
structures, and the «*_path» args uses regex to extract the arg from each pathname. 

For importing from several data files using args that need to be custom specified for each, the meta file
can also contain a json list of one or more such dicts. Args that stay the same dont have to be repeated
after the first dict. 

Lower admin levels can be derived from higher levels by specifying a list of json dicts referencing the same
file, where each dict specifies a different level, type, dissolve_field, and keep_fields. 
'''

import itertools
import os
import json
import re
import csv
import warnings

import shapefile as pyshp
from zipfile import ZipFile, ZIP_DEFLATED

# create iso lookup dict
iso2_to_3 = {}
iso3_to_name = {}
name_to_iso3 = {}
filedir = os.path.dirname(__file__)
with open(os.path.join(filedir, 'countries_codes_and_coordinates.csv'), encoding='utf8', newline='') as f:
    csvreader = csv.DictReader(f)
    for row in csvreader:
        name = row['Country'].strip().strip('"')
        iso2 = row['Alpha-2 code'].strip().strip('"')
        iso3 = row['Alpha-3 code'].strip().strip('"')
        iso2_to_3[iso2] = iso3
        iso3_to_name[iso3] = name
        name_to_iso3[name] = iso3

def get_reader(path, encoding='utf8'):
    # for now must be path to a shapefile within a zipfile
    zpath,shapefile = path[:path.find('.zip')+4], path[path.find('.zip')+4+1:]
    archive = ZipFile(zpath, 'r')
    shapefile = os.path.splitext(shapefile)[0] # root shapefile name
    # read file (pyshp)
    shp = archive.open(shapefile+'.shp')
    shx = archive.open(shapefile+'.shx')
    dbf = archive.open(shapefile+'.dbf')
    reader = pyshp.Reader(shp=shp, shx=shx, dbf=dbf, encoding=encoding)
    return reader

def inspect_data(path, numrows=3):
    if path.endswith('.zip'):
        # inspect all shapefiles inside zipfile
        archive = ZipFile(path, 'r')
        paths = [os.path.join(path, name)
                 for name in archive.namelist()
                 if name.endswith('.shp')]
    else:
        # inspect the specified zipfile member
        paths = [path]
    # inspect each file
    for path in paths:
        print('')
        print(path)
        reader = get_reader(path)
        for i,rec in enumerate(reader.iterRecords()):
            print(json.dumps(rec.as_dict(date_strings=True), sort_keys=True, indent=4))
            if i >= (numrows-1):
                break

def import_data(input_dir,
                input_path,
                collection,
                
                collection_subset=None,
                
                iso=None,
                iso_field=None,
                iso_path=None,
                level=None,
                level_field=None,
                level_path=None,
                type=None,
                type_field=None,
                year=None,
                year_field=None,
                
                name_field=None,
                source=None,
                source_updated=None,
                source_url=None,
                download_url=None,
                license=None,
                license_detail=None,
                license_url=None,
                
                dissolve=False,
                keep_fields=None,
                drop_fields=None,

                encoding='utf8',

                write_meta=True,
                write_stats=True,
                write_data=True,
                ):

    # define standard procedures
    
    def iter_paths(input_dir, input_path):
        # NOTE: input_path is relative to input_dir
        # this function returns the absolute path by joining them
        # ... 
        # path can be a single path, a path with regex wildcards, or list of paths
        if isinstance(input_path, str):
            if '*' in input_path:
                # regex
                pattern = input_path.replace('\\', '/')
                pattern = pattern.replace('*', '[^/]*')
                #raise Exception('Need to generalize this manual hardcoding for gadm...') # see next line
                zip_pattern = pattern.split('.zip')[0] + '.zip'
                print('regex', zip_pattern, pattern)
                for dirpath,dirnames,filenames in os.walk(os.path.abspath(input_dir)):
                    for filename in filenames:
                        zpath = os.path.join(dirpath, filename)
                        zpath = zpath.replace('\\', '/')
                        #print(zpath)
                        if re.search(zip_pattern, zpath):
                            #print('ZIPFILE MATCH')
                            archive = ZipFile(zpath, 'r')
                            for zmember in archive.namelist():
                                pth = os.path.join(zpath, zmember)
                                pth = pth.replace('\\', '/')
                                if re.search(pattern, pth):
                                    #print('ZIPFILE MEMBER MATCH')
                                    yield pth
            else:
                # single path
                yield os.path.join(input_dir, input_path)
                
        elif isinstance(input_path, list):
            # list of paths
            for pth in input_path:
                yield os.path.join(input_dir, pth)

    # prep source list
    sources = source if isinstance(source, list) else [source]

    # loop input files
    for path in iter_paths(input_dir, input_path):
        print('')
        print(path)

        # load the zipfile containing the shapefile
        #reader = get_reader(path, encoding)
        zipfile_path,zipfile_file = path.split('.zip')
        zipfile_path += '.zip'
        files = {'upload': open(zipfile_path, mode='rb')}

        # generate metadata
        # temp hack until all level fields are provided (only country and then lowest level)
        names = ['', '']
        name_fields = ['', name_field or '']
        # required:
        #names = []
        #name_fields = []
        #for lvl in range(level+1):
        #    names.append('')
        #    if lvl < level:
        #        # intermediary levels
        #        # for now we dont have info on intermediary name_field
        #        name_fields.append('')
        #    else:
        #        # last level
        #        name_fields.append(name_field or '') # None should be '', otherwise ignored in post reqest
        if year:
            datestring = str(year)
        elif source_updated:
            datestring = source_updated[-4:]

        # send shapefile and metadata as POST request to gbTracker website
        import requests
        url = 'http://127.0.0.1:8000/import_shapefile'
        data = {'date':datestring,
                'iso':iso,
                'iso_field':iso_field,
                'name':names,
                'name_field':name_fields,
                'source':sources,
                'zipfile_file':zipfile_file,
                'encoding':encoding,
                }
        print('POST', data)
        requests.post(url, data=data, files=files)

        continue

        # DELETE BELOW
        # iter country-levels
        for iso,level,feats in iter_country_level_feats(reader, path,
                                                        **iter_kwargs):
            print('')
            print('{}-ADM{}:'.format(iso, level), len(feats), 'admin units')

            # get year info
            if year is None:
                if year_field:
                    year = feats[0]['properties'][year_field] # for now just use the year of the first feature
            if not year:
                year = 'Unknown'

            # dissolve if specified
            if (write_data is True or write_stats is True) and dissolve:
                feats = dissolve_by(feats, dissolve, keep_fields, drop_fields)
                print('dissolved to', len(feats), 'admin units')

            # check that name_field is correct
            if name_field is not None:
                fields = feats[0]['properties'].keys()
                if name_field not in fields:
                    raise Exception("name_field arg '{}' is not a valid field; must be one of: {}".format(name_field, fields))

            # determine dataset name, in case multiple datasets (folders) inside folder
            dataset = collection
            if collection_subset:
                dataset += '_' + collection_subset

            # write data
            if write_data:
                print('writing data')

                # write geojson to zipfile
                # MAYBE ALSO ROUND TO 1e6, SHOULD DECR FILESIZE
                #zip_path = '{output}/{collection}/{iso}/ADM{lvl}/{dataset}-{iso}-ADM{lvl}-geojson.zip'.format(output=output_dir, dataset=dataset, collection=collection, iso=iso, lvl=level)
                #with ZipFile(zip_path, mode='w', compression=ZIP_DEFLATED) as archive:
                #    filename = '{dataset}-{iso}-ADM{lvl}.geojson'.format(output=output_dir, dataset=dataset, collection=collection, iso=iso, lvl=level)
                #    geoj = {'type':'FeatureCollection', 'features':feats}
                #    geoj_string = json.dumps(geoj)
                #    archive.writestr(filename, geoj_string)
                
                # create topology quantized to 1e6 (10cm) and delta encoded, greatly reduces filesize
                
                # NOTE: quantization isn't always the same as precision since it depends on the topology bounds
                # in some cases like USA (prob due to large extent?), precision degrades 3 decimals
                # INSTEAD added a custom precision arg to explicitly set decimal precision
                
                #if len(feats) == 1:
                #    print('only 1 object, creating topojson without topology')
                #    topo = tp.Topology(feats, topology=False, prequantize=1e6)
                #elif len(feats) > 1:
                #    try:
                #        print('> 1 objects, creating topojson with topology')
                #        topo = tp.Topology(feats, topology=True, prequantize=1e6)
                #    except:
                #        print('!!! failed to compute topology, creating topojson without topology')
                #        topo = tp.Topology(feats, topology=False, prequantize=1e6)
                print('creating quantized topojson (no topology optimization)')
                #topo = tp.Topology(feats, topology=False, prequantize=1e6)
                topo = topojson_simple.encode.topology({'features':feats}, precision=6)

                print('outputting to json')
                #topodata = topo.to_json()
                topodata = json.dumps(topo)

                # write topojson to zipfile
                print('writing to file')
                zip_path = '{output}/{collection}/{iso}/ADM{lvl}/{dataset}-{iso}-ADM{lvl}.topojson.zip'.format(output=output_dir, dataset=dataset, collection=collection, iso=iso, lvl=level)
                with ZipFile(zip_path, mode='w', compression=ZIP_DEFLATED) as archive:
                    filename = '{dataset}-{iso}-ADM{lvl}.topojson'.format(output=output_dir, dataset=dataset, collection=collection, iso=iso, lvl=level)
                    archive.writestr(filename, topodata)

            # update metadata
            meta = {
                    "boundaryYearRepresented": year,
                    "boundaryISO": iso,
                    "boundaryType": 'ADM{}'.format(int(level)),
                    "boundaryCanonical": type,
                    "boundaryLicense": license,
                    "nameField": name_field,
                    "licenseDetail": license_detail,
                    "licenseSource": license_url,
                    "boundarySourceURL": source_url,
                    "sourceDataUpdateDate": source_updated,
                    }
            for i,source in enumerate(sources):
                meta['boundarySource-{}'.format(i+1)] = source

