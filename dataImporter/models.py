from django.db import models

from changeManager.models import BoundarySource

# Create your models here.

class DataImporter(models.Model):
    source = models.OneToOneField(BoundarySource, related_name='importer', on_delete=models.PROTECT)
    import_params = models.JSONField(blank=True, null=True)

# class DataImporter(models.Model):
#     source = models.OneToOneField('BoundarySource', related_name='importer')
#     fetch_url = models.URLField() # url to the raw data file to import data from
#     zipfile_file = models.CharField(max_length=1000)
#     encoding = models.CharField(max_length=255)
#     levels = models.ForeignKey('LevelDefinition', related_name='importer')

# class LevelDefinition(models.Model):
#     level = models.IntegerField(null=True, blank=True)
#     # name can be staticly defined from 'names', or dynamically from 'name_fields' (comma separated)
#     name_fields = models.CharField(max_length=1000)
#     names = models.ForeignKey('BoundaryName', related_name='+')
#     # code can be staticly defined from 'codes', or dynamically from 'code_fields' (comma separated)
#     code_fields = models.CharField(max_length=1000) 
#     codes = models.ForeignKey('BoundaryCode', related_name='+')
