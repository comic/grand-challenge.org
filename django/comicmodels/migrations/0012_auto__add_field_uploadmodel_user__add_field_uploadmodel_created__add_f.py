# -*- coding: utf-8 -*-
import pdb
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.contrib.auth.models import User


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'UploadModel.user'
        
        db.add_column('comicmodels_uploadmodel', 'user',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, null=True, to=orm['auth.User']),
                      keep_default=False)
        

        # Adding field 'UploadModel.created'
        db.add_column('comicmodels_uploadmodel', 'created',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.date.today, auto_now_add=True, blank=True),
                      keep_default=False)

        # Adding field 'UploadModel.modified'
        db.add_column('comicmodels_uploadmodel', 'modified',
                      self.gf('django.db.models.fields.DateTimeField')(default=datetime.date.today, auto_now=True, blank=True),
                      keep_default=False)


        if not db.dry_run:
                        
            if(orm['auth.user'].objects.filter(username='root').count() > 0):
                print "Setting user for any existing uploaded files to 'root' user"                
                rootuser =  orm['auth.user'].objects.get(username='root')
               
                for uploadmodel in orm['comicmodels.UploadModel'].objects.all():                            
                    uploadmodel.user = rootuser                
                    uploadmodel.save()
            else:
                pass
                print "No user 'root' found. Not changing any uploaded files"


    def backwards(self, orm):
        # Deleting field 'UploadModel.user'
        db.delete_column('comicmodels_uploadmodel', 'user_id')

        # Deleting field 'UploadModel.created'
        db.delete_column('comicmodels_uploadmodel', 'created')

        # Deleting field 'UploadModel.modified'
        db.delete_column('comicmodels_uploadmodel', 'modified')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'comicmodels.comicsite': {
            'Meta': {'object_name': 'ComicSite'},
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.URLField', [], {'default': "'http://www.grand-challenge.org/images/a/a7/Grey.png'", 'max_length': '200'}),
            'short_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'skin': ('django.db.models.fields.CharField', [], {'max_length': '225', 'blank': 'True'})
        },
        'comicmodels.dropboxfolder': {
            'Meta': {'object_name': 'DropboxFolder'},
            'access_token_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'access_token_secret': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'comicsite': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comicmodels.ComicSite']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_status_msg': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1023', 'blank': 'True'}),
            'permission_lvl': ('django.db.models.fields.CharField', [], {'default': "'ALL'", 'max_length': '3'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
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
            'created': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'auto_now': 'True', 'blank': 'True'}),
            'permission_lvl': ('django.db.models.fields.CharField', [], {'default': "'ALL'", 'max_length': '3'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
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