# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # faking model creation so django will update permissions. Took me an hour to find this. 
        # see http://dev.markhaus.com/blog/2011/04/django-admin-permissions-and-contenttype-table-doesnt-update-when-adding-proxy-models/
        db.send_create_signal('comicmodels', ['filesystemdataset'])


    def backwards(self, orm):
        pass

    models = {
        'comicmodels.comicsite': {
            'Meta': {'object_name': 'ComicSite'},
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.URLField', [], {'default': "'http://www.grand-challenge.org/images/a/a7/Grey.png'", 'max_length': '200'}),
            'short_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'skin': ('django.db.models.fields.CharField', [], {'max_length': '225', 'blank': 'True'})
        },
        'comicmodels.filesystemdataset': {
            'Meta': {'object_name': 'FileSystemDataset'},
            'comicsite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comicmodels.ComicSite']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'folder': ('django.db.models.fields.FilePathField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permission_lvl': ('django.db.models.fields.CharField', [], {'default': "'ALL'", 'max_length': '3'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'comicmodels.page': {
            'Meta': {'ordering': "['comicsite', 'order']", 'unique_together': "(('comicsite', 'title'),)", 'object_name': 'Page'},
            'comicsite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comicmodels.ComicSite']"}),
            'display_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'html': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'permission_lvl': ('django.db.models.fields.CharField', [], {'default': "'ALL'", 'max_length': '3'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'comicmodels.uploadmodel': {
            'Meta': {'object_name': 'UploadModel'},
            'comicsite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comicmodels.ComicSite']"}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permission_lvl': ('django.db.models.fields.CharField', [], {'default': "'ALL'", 'max_length': '3'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        }
    }

    complete_apps = ['comicmodels', 'comicmodels']