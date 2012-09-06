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

        # Adding model 'ComicSite'
        db.create_table('comicsite_comicsite', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('short_name', self.gf('django.db.models.fields.CharField')(default='', max_length=50)),
            ('skin', self.gf('django.db.models.fields.CharField')(max_length=225)),
            ('comment', self.gf('django.db.models.fields.CharField')(default='', max_length=1024, blank=True)),
        ))
        db.send_create_signal('comicsite', ['ComicSite'])

        # Adding model 'Page'
        db.create_table('comicsite_page', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('ComicSite', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['comicsite.ComicSite'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('html', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('comicsite', ['Page'])

        # Adding unique constraint on 'Page', fields ['ComicSite', 'title']
        db.create_unique('comicsite_page', ['ComicSite_id', 'title'])


    def backwards(self, orm):
        # Removing unique constraint on 'Page', fields ['ComicSite', 'title']
        db.delete_unique('comicsite_page', ['ComicSite_id', 'title'])

        # Deleting model 'ComicSiteModel'
        db.delete_table('comicsite_comicsitemodel')

        # Deleting model 'ComicSite'
        db.delete_table('comicsite_comicsite')

        # Deleting model 'Page'
        db.delete_table('comicsite_page')


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