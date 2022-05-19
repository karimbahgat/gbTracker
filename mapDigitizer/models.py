from django.db import models

import json

# Create your models here.

class MapDigitizer(models.Model):
    source = models.OneToOneField("changeManager.BoundarySource", related_name='digitizer', on_delete=models.PROTECT)
    digitized_data = models.JSONField(blank=True, null=True)
    last_digitized = models.DateTimeField(null=True, blank=True)

    @property
    def digitized_data_json(self):
        return json.dumps(self.digitized_data)
