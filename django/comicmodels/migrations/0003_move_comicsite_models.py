# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ComicSite'
        db.rename_table('comicsite_comicsite', 'comicmodels_comicsite') 
        
        if not db.dry_run:
            # For permissions to work properly after migrating
            orm['contenttypes.contenttype'].objects.filter(app_label='comicsite', model='comicsite').update(app_label='comicmodels')
        
        
        db.rename_table('comicsite_page', 'comicmodels_page') 
        
        # Adding model 'Page'
        if not db.dry_run:
            # For permissions to work properly after migrating
            orm['contenttypes.contenttype'].objects.filter(app_label='comicsite', model='page').update(app_label='comicmodels')
        


    def backwards(self, orm):
        # Adding model 'ComicSite'
        db.rename_table('comicmodels_comicsite', 'comicsite_comicsite') 
        
        if not db.dry_run:
            # For permissions to work properly after migrating
            orm['contenttypes.contenttype'].objects.filter(app_label='comicmodels', model='comicsite').update(app_label='comicsite')
        
        
        db.rename_table('comicsite_page', 'comicmodels_page') 
        
        # Adding model 'Page'
        if not db.dry_run:
            # For permissions to work properly after migrating
            orm['contenttypes.contenttype'].objects.filter(app_label='comicmodels', model='page').update(app_label='comicsite')


    models = {
        'comicmodels.comicsite': {
            'Meta': {'object_name': 'ComicSite'},
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200'}),
            'short_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'skin': ('django.db.models.fields.CharField', [], {'max_length': '225'})
        },
        'comicmodels.filesystemdataset': {
            'Meta': {'object_name': 'FileSystemDataset'},
            'comicsite': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['comicmodels.ComicSite']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'folder': ('django.db.models.fields.FilePathField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'comicmodels.page': {
            'ComicSite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comicmodels.ComicSite']"}),
            'Meta': {'ordering': "['ComicSite', 'order']", 'unique_together': "(('ComicSite', 'title'),)", 'object_name': 'Page'},
            'display_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'html': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'comicmodels.uploadmodel': {
            'Meta': {'object_name': 'UploadModel'},
            'comicsite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comicmodels.ComicSite']"}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['comicmodels',]