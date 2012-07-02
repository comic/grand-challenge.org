# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Give each page an order. For default, take pages of each site and number them 1 to n"
        # Note: Remember to use orm['appname.ModelName'] rather than "from appname.models..."
        
        for comicsite in orm.ComicSite.objects.all():
            count = 0            
            pages = orm.Page.objects.filter(ComicSite__short_name=comicsite.short_name)
            for page in pages:
                count += 1
                page.order = count
                page.save()    
            
    def backwards(self, orm):
        "To go back, set all order params to default, which is one 1."
        for page in orm.Page.objects.all():
            page.order = 1
            page.save()
            

    models = {
        'comicsite.comicsite': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'ComicSite', '_ormbases': ['sites.Site']},
            'comment': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'site_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sites.Site']", 'unique': 'True', 'primary_key': 'True'}),
            'skin': ('django.db.models.fields.CharField', [], {'max_length': '225'})
        },
        'comicsite.page': {
            'ComicSite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comicsite.ComicSite']"}),
            'Meta': {'unique_together': "(('ComicSite', 'title'),)", 'object_name': 'Page'},
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
