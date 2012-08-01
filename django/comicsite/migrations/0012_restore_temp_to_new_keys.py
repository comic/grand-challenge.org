# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
import pdb
from copy import deepcopy

class Migration(DataMigration):

    def forwards(self, orm):
        "Save the id of the base site object for this comicsite. Later on the base site can be removed and this temp value placed in comicsite.id"
        for comicsite in orm.ComicSite.objects.all():
            
            new_comicsite = deepcopy(comicsite)
            new_comicsite.id = comicsite.id_temp #comicsite.id resolves to site.id automatically
            comicsite.delete()
            new_comicsite.save()             
            
        #for comicsite in orm.ComicSite.objects.filter(id=id_temp):
                        
            #comicsite.id = comicsite.id_temp #comicsite.id resolves to site.id automatically
            #comicsite.save()
        
        for page in orm.Page.objects.all():
            
            comicsiteInstance = orm.ComicSite.objects.get(id__exact=page.ComicSiteTemp)          
            page.ComicSite = comicsiteInstance #comicsite.id resolves to site.id automatically
            page.save()
            
    def backwards(self, orm):        
        "Write your forwards methods here."
        print "comicsite.id can not be restored. Keeping current ids"
        
        qs = orm.ComicSite.objects.all()
        
        
        for page in orm.Page.objects.all():
            
            page.ComicSite = qs[0] 
            page.save()


    models = {
        'comicsite.comicsite': {
            'Meta': {'object_name': 'ComicSite'},
            'comment': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'id_temp': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'short_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'skin': ('django.db.models.fields.CharField', [], {'max_length': '225'})
        },
        'comicsite.comicsitemodel': {
            'Meta': {'object_name': 'ComicSiteModel'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'comicsite.page': {
            'ComicSite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comicsite.ComicSite']"}),
            'ComicSiteTemp': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'Meta': {'object_name': 'Page'},
            'html': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['comicsite']
    symmetrical = True
