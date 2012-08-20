# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ComicSiteModel'
        db.create_table('comicsite_comicsitemodel', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('comicsite', ['ComicSiteModel'])

        # Adding field 'ComicSite.id_temp'
        db.add_column('comicsite_comicsite', 'id_temp',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)

        # Adding field 'Page.ComicSiteTemp'
        db.add_column('comicsite_page', 'ComicSiteTemp',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'ComicSiteModel'
        db.delete_table('comicsite_comicsitemodel')

        # Deleting field 'ComicSite.id_temp'
        db.delete_column('comicsite_comicsite', 'id_temp')

        # Deleting field 'Page.ComicSiteTemp'
        db.delete_column('comicsite_page', 'ComicSiteTemp')


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