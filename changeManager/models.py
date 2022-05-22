from django.db import models

from django.forms.models import model_to_dict

from djangowkb.fields import GeometryField

# Create your models here.

SOURCE_TYPES = [
    ('TextSource', 'Text Source'),
    ('DataSource', 'Data Source'),
    ('MapSource', 'Map Source'),
]

class BoundarySource(models.Model):
    type = models.CharField(max_length=50,
                            choices=SOURCE_TYPES)
    name = models.CharField(max_length=200)
    #created_by = ... # this should be a required User reference
    #last_updated = models.DateTimeField(auto_now=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    citation = models.TextField(blank=True, null=True)
    #lineage = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)

class BoundaryReference(models.Model):
    parent = models.ForeignKey('BoundaryReference', related_name='children', on_delete=models.CASCADE, 
                                blank=True, null=True)
    source = models.ForeignKey('BoundarySource', related_name='boundary_refs', on_delete=models.CASCADE, 
                                blank=True, null=True)
    names = models.ManyToManyField('BoundaryName', related_name='boundary_refs')
    codes = models.ManyToManyField('BoundaryCode', related_name='boundary_refs')
    level = models.IntegerField(null=True, blank=True) # just to indicate the self-described admin-level of the ref

    def get_all_parents(self, include_self=True):
        '''Returns a list of all parents, starting with and including self.'''
        refs = [self]
        cur = self
        while cur.parent:
            cur = cur.parent
            refs.append(cur)
        return refs

    def get_all_children(self):
        '''Returns a list of all children.'''
        results = []
        for child in self.children.all():
            subchildren = child.get_all_children()
            results.append( {'item':child, 'children':subchildren} )
        return results

    def full_name(self):
        all_refs = self.get_all_parents()
        full_name = ', '.join([ref.names.first().name for ref in all_refs])
        return full_name

    def serialize(self, snapshots=True):
        boundary_refs = [{'id':p.id, 'names':[n.name for n in p.names.all()], 'level':p.level}
                        for p in self.get_all_parents()]
        source = self.source
        dct = {'id':self.pk,
                'boundary_refs':boundary_refs,
                'source':{'name':source.name, 'id':source.pk},
                }
        if snapshots:
            snaps = [{'event':model_to_dict(snap.event), 'geom':snap.geom.__geo_interface__}
                    for snap in self.snapshots.all()]
            dct['snapshots'] = snaps
        return dct

class BoundaryName(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        indexes = [
            models.Index(fields=['name']), # not case insensitive though... 
        ]

class BoundaryCode(models.Model):
   code_type = models.ForeignKey('CodeType', related_name='+', on_delete=models.PROTECT)
   code = models.CharField(max_length=100)

class CodeType(models.Model):
   name = models.CharField(max_length=100)
   description = models.CharField(max_length=255)


# Boundary changes

class Event(models.Model):
    date_start = models.CharField(max_length=16)
    date_end = models.CharField(max_length=16)

class BoundarySnapshot(models.Model):
    event = models.ForeignKey('Event', related_name='snapshots', on_delete=models.CASCADE)
    boundary_ref = models.ForeignKey('BoundaryReference', related_name='snapshots', on_delete=models.CASCADE)
    geom = GeometryField()
