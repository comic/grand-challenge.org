# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from guardian.shortcuts import assign_perm
from django.contrib.auth.models import Group,Permission
 


class Migration(SchemaMigration):

    def forwards(self, orm):
        if not db.dry_run:
            # some object classes can only be seen by root, like all users for
            # instance. Add the new object class RegistrationRequest to the group
            # which all project admins are part of, so they don't get a 403 forbidden
            # when trying to see requests for their project 
                                    
            try:                                                               
                projectadmins = Group.objects.get(name="projectadmins")
            except Group.DoesNotExist as e:                            
                projectadmins = Group(name='projectadmins')
                #TODO add permissions for all comicmodels and registrationRequest
                projectadmins.save()
                 
            # my god spent 2 hours on this line. But this fixes any issues with
            # default permissions for registrationrequest not being found..
            db.send_pending_create_signals()
                        
            # each user in comic is part of this group projectadmins. With the
            # permission in this group you can determine which types of objects
            # regular adins can see and edit in the admin interface.
                
            self.add_standard_perms("comicmodels","registrationrequest",projectadmins)
            self.add_standard_perms("comicmodels","comicsite",projectadmins)
            self.add_standard_perms("comicmodels","page",projectadmins)                                    
            
    
    def add_standard_perms(self,appname,modelname,group):
        assign_perm("{0}.add_{1}".format(appname,modelname),group)
        assign_perm("{0}.change_{1}".format(appname,modelname),group)
        assign_perm("{0}.delete_{1}".format(appname,modelname),group)
        
                             
    def backwards(self, orm):
        pass

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'comicmodels.comicsite': {
            'Meta': {'object_name': 'ComicSite'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024', 'blank': 'True'}),
            'disclaimer': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '2048', 'null': 'True', 'blank': 'True'}),
            'event_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'event_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'header_image': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hide_footer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'hide_signin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.CharField', [], {'default': "'public_html/logo.png'", 'max_length': '255'}),
            'offers_data_download': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'require_participant_review': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'short_name': ('django.db.models.fields.SlugField', [], {'default': "''", 'max_length': '50'}),
            'skin': ('django.db.models.fields.CharField', [], {'default': "'public_html/project.css'", 'max_length': '225'}),
            'workshop_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'})
        },
        u'comicmodels.dropboxfolder': {
            'Meta': {'object_name': 'DropboxFolder'},
            'access_token_key': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'access_token_secret': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'comicsite': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['comicmodels.ComicSite']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_status_msg': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1023', 'blank': 'True'}),
            'permission_lvl': ('django.db.models.fields.CharField', [], {'default': "'ALL'", 'max_length': '3'}),
            'title': ('django.db.models.fields.SlugField', [], {'max_length': '64', 'blank': 'True'})
        },
        u'comicmodels.filesystemdataset': {
            'Meta': {'object_name': 'FileSystemDataset'},
            'comicsite': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['comicmodels.ComicSite']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'folder': ('django.db.models.fields.FilePathField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permission_lvl': ('django.db.models.fields.CharField', [], {'default': "'ALL'", 'max_length': '3'}),
            'title': ('django.db.models.fields.SlugField', [], {'max_length': '64', 'blank': 'True'})
        },
        u'comicmodels.page': {
            'Meta': {'ordering': "['comicsite', 'order']", 'unique_together': "(('comicsite', 'title'),)", 'object_name': 'Page'},
            'comicsite': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['comicmodels.ComicSite']"}),
            'display_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'html': ('ckeditor.fields.RichTextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'permission_lvl': ('django.db.models.fields.CharField', [], {'default': "'ALL'", 'max_length': '3'}),
            'title': ('django.db.models.fields.SlugField', [], {'max_length': '64', 'blank': 'True'})
        },
        u'comicmodels.registrationrequest': {
            'Meta': {'object_name': 'RegistrationRequest'},
            'changed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date.today', 'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['comicmodels.ComicSite']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'PEND'", 'max_length': '4'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'comicmodels.uploadmodel': {
            'Meta': {'object_name': 'UploadModel'},
            'comicsite': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['comicmodels.ComicSite']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date.today', 'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date.today', 'auto_now': 'True', 'blank': 'True'}),
            'permission_lvl': ('django.db.models.fields.CharField', [], {'default': "'ALL'", 'max_length': '3'}),
            'title': ('django.db.models.fields.SlugField', [], {'max_length': '64', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['comicmodels']