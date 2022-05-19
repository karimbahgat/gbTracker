from django.db import models

# Create your models here.

class MapDigitizer(models.Model):
    source = models.OneToOneField("changeManager.BoundarySource", related_name='digitizer', on_delete=models.PROTECT)
    digitized_data = models.JSONField(blank=True, null=True)
    last_digitized = models.DateTimeField(null=True, blank=True)
