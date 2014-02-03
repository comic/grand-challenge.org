# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from thirdparty import dingus
import pdb


class Migration(SchemaMigration):

    def forwards(self, orm):        
        # Removing unique constraint on 'Page', fields ['ComicSite', 'title']
        #db.delete_unique('comicmodels_page', ['ComicSite_id', 'title'])
        
         
        db.rename_column('comicmodels_page', 'ComicSite_id', 'comicsite_id')

        
        # Load initial data, so when setting up for the first time there is at
        # least a single project and a page. This command should be in 
        # 0001_initial but was added after
        # why the dingus.loaddata? See http://stackoverflow.com/questions/5472925/django-loading-data-from-fixture-after-backward-migration-loaddata-is-using-mo/5906258#5906258
        dingus.loaddata(orm,"comic_initial_project.json")        


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
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['comicmodels']