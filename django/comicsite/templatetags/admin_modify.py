from django import template

import django.contrib.admin.templatetags.admin_modify as original 

register = template.Library()

#For some reason importing these functions does not work. Explicitly calling them
@register.inclusion_tag('admin/prepopulated_fields_js.html', takes_context=True)
def prepopulated_fields_js(context):
    return original.prepopulated_fields_js(context)

@register.inclusion_tag('admin/submit_line.html', takes_context=True)
def submit_row(context):
    """
    Displays the row of buttons for delete and save. Including projectname
    here so projectadmin can redirect to correctproject after saving,deleting
    """
    ctx = original.submit_row(context)
    ctx["site"] = context["site"]
    return ctx
    

@register.filter
def cell_count(inline_admin_form):
    return original.cell_count(inline_admin_form)