# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
    ('comicmodels', '0003_move_comicsite_models'),
)

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        
    }

    complete_apps = ['comicsite']