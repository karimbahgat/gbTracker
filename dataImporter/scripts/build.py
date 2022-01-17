
import iotools
import os
import json
import warnings
import traceback
import sys
from datetime import datetime

# params
folder = 'C:/Users/kimok/Documents/Github/geoContrast'
collections = ['WFP','Natural_Earth','GADM'] #['IPUMS','Other','SALB']
isos = [] #['NOR','CHL','CAN','FRA','USA']
replace = False
write_meta = True
write_stats = True
write_data = True

# redirect to logfile
#logger = open('build_log.txt', mode='w', encoding='utf8', buffering=1)
#sys.stdout = logger
#sys.stderr = logger

# begin
os.chdir(folder)
print('start time', datetime.now())
for dirpath,dirnames,filenames in os.walk('sourceData'):
    if 'sourceMetaData.json' in filenames:
        # load kwargs from meta file
        with open(os.path.join(dirpath, 'sourceMetaData.json'), encoding='utf8') as fobj:
            kwargs = json.loads(fobj.read())

        # determine the dataset name from the folder below sourceData
        reldirpath = os.path.relpath(dirpath, 'sourceData')
        collection = reldirpath.split('/')[0].split('\\')[0] # topmost folder

        # only process if collection is in the list of collections to be processed
        if collections and collection not in collections:
            continue

        # only process if iso is in the list isos to be processed
        # (only for iso-specific sources for now)
        if 'iso' in kwargs:
            # this is an iso-specific source
            if isos and kwargs['iso'] not in isos:
                continue
        
        print('')
        print('='*30)
        print('processing', dirpath)

        # add final entries to kwargs
        kwargs.update(input_dir=dirpath,
                      collection=collection,
                      write_meta=write_meta,
                      write_stats=write_stats,
                      write_data=write_data)

        print('')
        print('reading sourceMetaData.json')

        # nest multiple inputs
        if 'input' not in kwargs:
            warnings.warn("metadata file for '{}' doesn't have correct format, skipping".format(dirpath))
            continue
        input_arg = kwargs.pop('input')
        if isinstance(input_arg, str):
            inputs = [{'path':input_arg}]
        elif isinstance(input_arg, list):
            inputs = input_arg
        else:
            raise Exception('input arg must be either string or list of dicts')
        # run one or more imports
        for input_kwargs in inputs:
            _kwargs = kwargs.copy()
            _kwargs.update(input_kwargs)
            _kwargs['input_path'] = _kwargs.pop('path') # rename path arg
            print('')
            print('-'*30)
            print('import args', _kwargs)
            try:
                iotools.import_data(**_kwargs)
            except Exception as err:
                warnings.warn("Error importing data for '{}': {}".format(dirpath, traceback.format_exc()))
                
print('end time', datetime.now())

#logger.close()
