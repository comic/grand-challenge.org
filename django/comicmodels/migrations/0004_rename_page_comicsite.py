# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
import pdb


class Migration(SchemaMigration):

    def forwards(self, orm):        
        # Removing unique constraint on 'Page', fields ['ComicSite', 'title']
        #db.delete_unique('comicmodels_page', ['ComicSite_id', 'title'])
        
         
        db.rename_column('comicmodels_page', 'ComicSite_id', 'comicsite_id')

        # Adding unique constraint on 'Page', fields ['comicsite', 'title']
        #db.create_unique('comicmodels_page', ['comicsite_id', 'title'])


    def backwards(self, orm):
        # Removing unique constraint on 'Page', fields ['comicsite', 'title']
        db.delete_unique('comicmodels_page', ['comicsite_id', 'title'])

        
        db.rename_column('comicmodels_page', 'comicsite_id', 'ComicSite_id')
        
        # Adding unique constraint on 'Page', fields ['ComicSite', 'title']
        db.create_unique('comicmodels_page', ['ComicSite_id', 'title'])


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
            'Meta': {'ordering': "['comicsite', 'order']", 'unique_together': "(('comicsite', 'title'),)", 'object_name': 'Page'},
            'comicsite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comicmodels.ComicSite']"}),
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
        }
    }

    complete_apps = ['comicmodels']