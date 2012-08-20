# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
import pdb

class Migration(DataMigration):

    def forwards(self, orm):
        "Save the id of the base site object for this comicsite. Later on the base site can be removed and this temp value placed in comicsite.id"
        for comicsite in orm.ComicSite.objects.all():
            comicsite.id_temp = comicsite.id #comicsite.id resolves to site.id automatically
            comicsite.save()             
        
        for page in orm.Page.objects.all():
            pdb.set_trace()
            page.ComicSiteTemp = page.ComicSite.id #comicsite.id resolves to site.id automatically
            page.save()
            
    def backwards(self, orm):        
        "Write your forwards methods here."
        for comicsite in orm.ComicSite.objects.all():
            comicsite.id_temp = 0
            comicsite.save()
        
        for page in orm.Page.objects.all():
            page.ComicSiteTemp = 0
            page.save()

    models = {
        'comicsite.comicsite': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'ComicSite', '_ormbases': ['sites.Site']},
            'comment': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'id_temp': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'short_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'site_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sites.Site']", 'unique': 'True', 'primary_key': 'True'}),
            'skin': ('django.db.models.fields.CharField', [], {'max_length': '225'})
        },
        'comicsite.comicsitemodel': {
            'Meta': {'object_name': 'ComicSiteModel'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'comicsite.page': {
            'ComicSite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comicsite.ComicSite']"}),
            'ComicSiteTemp': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'Meta': {'ordering': "['ComicSite', 'order']", 'unique_together': "(('ComicSite', 'title'),)", 'object_name': 'Page'},
            'html': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['comicsite']
    symmetrical = True
