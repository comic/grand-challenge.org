from django.core.urlresolvers import reverse
from django import template
from django.contrib.admin.util import quote

register = template.Library()

"""
Copied these from django/contrib/admin/templates/templatetags/admin_urls.
These are utility functions for generating urls to admin pages.
I want to extend the standard /admin url to always include the current project,
designated by /site/<projectname>/admin. 
"""

@register.filter
def project_admin_urlname(value, arg):    
    return 'projectadmin:%s_%s_%s' % (value.app_label, value.module_name, arg)

@register.filter
def project_admin_urlquote(value):
    return quote(value)
