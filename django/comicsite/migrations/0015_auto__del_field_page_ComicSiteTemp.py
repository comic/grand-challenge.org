# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Page.ComicSiteTemp'
        db.delete_column('comicsite_page', 'ComicSiteTemp')


    def backwards(self, orm):
        # Adding field 'Page.ComicSiteTemp'
        db.add_column('comicsite_page', 'ComicSiteTemp',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


    models = {
        'comicsite.comicsite': {
            'Meta': {'object_name': 'ComicSite'},
            'comment': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'skin': ('django.db.models.fields.CharField', [], {'max_length': '225'})
        },
        'comicsite.comicsitemodel': {
            'Meta': {'object_name': 'ComicSiteModel'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'comicsite.page': {
            'ComicSite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comicsite.ComicSite']"}),
            'Meta': {'ordering': "['ComicSite', 'order']", 'unique_together': "(('ComicSite', 'title'),)", 'object_name': 'Page'},
            'html': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['comicsite']