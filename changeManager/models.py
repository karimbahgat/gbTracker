from django.db import models

from djangowkb.fields import GeometryField

# Create your models here.

class BoundaryReference(models.Model):
    parent = models.ForeignKey('BoundaryReference', related_name='children', on_delete=models.PROTECT, 
                                blank=True, null=True)
    names = models.ManyToManyField('BoundaryName', related_name='boundary_refs')

    def get_all_parents(self, include_self=True):
        '''Returns a list of all parents, starting with and including self.'''
        refs = [self]
        cur = self
        while cur.parent:
            cur = cur.parent
            refs.append(cur)
        return refs

    #def get_all_children(self):
    #    '''Returns a list of all parents, starting with and including self.'''
    #    refs = [self]
    #    cur = self
    #    if cur.children:
    #        refs.extend(self.children)
    #    return refs

class BoundaryName(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        indexes = [
            models.Index(fields=['name']), # not case insensitive though... 
        ]

#class BoundaryCode(models.Model):
#    boundary_ref = models.ForeignKey('BoundaryReference', related_name='codes')
#    code_type = models.ForeignKey('CodeType', related_name='+')
#    code = models.CharField(max_length=10)

#class CodeType(models.Model):
#    name = models.CharField(max_length=100)
#    description = models.CharField(max_length=255)


# Boundary changes

class Event(models.Model):
    date_start = models.CharField(max_length=16)
    date_end = models.CharField(max_length=16)

class BoundarySnapshot(models.Model):
    event = models.ForeignKey('Event', related_name='snapshots', on_delete=models.CASCADE)
    boundary_ref = models.ForeignKey('BoundaryReference', related_name='snapshots', on_delete=models.CASCADE)
    geom = GeometryField()
    source = models.CharField(max_length=100)
