nov 2012 Sjoerd

This dir contains copies of django 1.4.1 contrib\templates\

You cannot override site wide templates directly without recursion errors.
For example, a custom /admin/base.html {% extends admin/base.html %} will try to 
include itself instead of the default base.html in django.

To overcome this I copy the original django templates here.

== Updates ==
- Django 1.8.18
