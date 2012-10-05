# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Page', fields ['ComicSite', 'title']
        db.delete_unique('comicsite_page', ['ComicSite_id', 'title'])

        # Deleting model 'ComicSite'
        db.delete_table('comicsite_comicsite')

        # Deleting model 'ComicSiteModel'
        db.delete_table('comicsite_comicsitemodel')

        # Deleting model 'Page'
        db.delete_table('comicsite_page')


    def backwards(self, orm):
        # Adding model 'ComicSite'
        db.create_table('comicsite_comicsite', (
            ('description', self.gf('django.db.models.fields.CharField')(default='', max_length=1024, blank=True)),
            ('short_name', self.gf('django.db.models.fields.CharField')(default='', max_length=50)),
            ('skin', self.gf('django.db.models.fields.CharField')(max_length=225)),
            ('logo', self.gf('django.db.models.fields.URLField')(default='', max_length=200)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('comicsite', ['ComicSite'])

        # Adding model 'ComicSiteModel'
        db.create_table('comicsite_comicsitemodel', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('comicsite', ['ComicSiteModel'])

        # Adding model 'Page'
        db.create_table('comicsite_page', (
            ('order', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('hidden', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('ComicSite', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['comicsite.ComicSite'])),
            ('display_title', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True)),
            ('html', self.gf('django.db.models.fields.TextField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('comicsite', ['Page'])

        # Adding unique constraint on 'Page', fields ['ComicSite', 'title']
        db.create_unique('comicsite_page', ['ComicSite_id', 'title'])


    models = {
        
    }

    complete_apps = ['comicsite']