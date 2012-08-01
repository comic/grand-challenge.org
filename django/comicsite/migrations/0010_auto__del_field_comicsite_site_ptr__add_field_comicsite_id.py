# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'ComicSite.site_ptr'
        db.delete_column('comicsite_comicsite', 'site_ptr_id')

        # Adding field 'ComicSite.id'
        db.add_column('comicsite_comicsite', 'id',
                      self.gf('django.db.models.fields.AutoField')(default=None, primary_key=True),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'ComicSite.site_ptr'
        db.add_column('comicsite_comicsite', 'site_ptr',
                      self.gf('django.db.models.fields.related.OneToOneField')(default=None, to=orm['sites.Site'], unique=True, primary_key=True),
                      keep_default=False)

        # Deleting field 'ComicSite.id'
        db.delete_column('comicsite_comicsite', 'id')


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
            'ComicSiteTemp': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'Meta': {'object_name': 'Page'},
            'html': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['comicsite']