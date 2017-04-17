import pdb
from django.db import models
from django import forms

from ckeditor.widgets import CKEditorWidget


class RichTextField(models.TextField):
    def __init__(self, *args, **kwargs):        
        self.config_name = kwargs.pop("config_name", "default")
        super(RichTextField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': RichTextFormField,
            'config_name': self.config_name,
        }
        defaults.update(kwargs)
        return super(RichTextField, self).formfield(**defaults)


class RichTextFormField(forms.fields.Field):
    def __init__(self, config_name='default', *args, **kwargs):        
        kwargs.update({'widget': CKEditorWidget(config_name=config_name)})
        if 'max_length' in kwargs:
            del kwargs['max_length']
        super(RichTextFormField, self).__init__(*args, **kwargs)
        
        
    def widget_attrs(self, widget):
        """
        Given a Widget instance (*not* a Widget class), returns a dictionary of
        any HTML attributes that should be added to the Widget, based on this
        Field.
        """
        
        return {"jemoeder":True}

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^ckeditor\.fields\.RichTextField"])
except:
    pass
