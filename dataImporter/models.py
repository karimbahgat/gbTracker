from django.db import models

# from changeManager.models import BoundarySource, BoundaryName, BoundaryCode


# # Create your models here.
# class DataImporter(models.Model):
#     source = models.OneToOneField(BoundarySource, related_name='importer')
#     fetch_url = models.URLField() # url to the raw data file to import data from
#     zipfile_file = models.CharField(max_length=1000)
#     encoding = models.CharField(max_length=255)
#     levels = models.ForeignKey(LevelDefinition, related_name='importer')

# class LevelDefinition(models.Model):
#     level = models.IntegerField(null=True, blank=True)
#     # name can be staticly defined from 'names', or dynamically from 'name_fields'
#     name_fields = models.ForeignKey(BoundaryName, related_name='+')
#     names = models.ForeignKey(BoundaryName, related_name='+')
#     # code can be staticly defined from 'codes', or dynamically from 'code_fields'
#     code_fields = models.ForeignKey(BoundaryCode, related_name='+')
#     codes = models.ForeignKey(BoundaryCode, related_name='+')
