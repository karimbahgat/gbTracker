from django.db import models

from djangowkb.fields import GeometryField

# Create your models here.

class BoundaryReference(models.Model):
    parent = models.ForeignKey('BoundaryReference', related_name='children', on_delete=models.PROTECT, 
                                blank=True, null=True)

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

    """
    def match_references(self):
        '''Returns a list of matching boundary_refs based on either the name or code of self.
        Each match is returned along with given a match score.
        '''
        matches = BoundaryReference.objects.filter(names__name=self.names)
        return matches

    def match_snapshots(self):
        '''Returns a list of matching snapshots based on either the name or code of self.
        Each match is returned along with given a match score.
        '''
        print('names',self.names)
        matches = BoundarySnapshot.objects.filter(boundary_ref__names__name=self.names)
        print('matches',matches)
        return matches
    """

class BoundaryName(models.Model):
    boundary_ref = models.ForeignKey('BoundaryReference', related_name='names', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

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
