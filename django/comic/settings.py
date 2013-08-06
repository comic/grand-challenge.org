# Django settings for comic project.
import os
import glob 
from django.core.exceptions import ImproperlyConfigured


# Get *.conf from the directory this file is in and execute these in order. 
# To include your own local settings, put these in a  a 'XX-local.conf' file in the
# current dir. XX should be a number which determines the order of execution. 
# Executed last overwrites previous settings.  

path = os.path.join(os.path.dirname(__file__), 'settings', '*.conf')
conffiles = glob.glob(path)

if(len(conffiles) == 0):
    msg = "Could not find any files matching '" + path + "'. There should be at least one configuration file containing django settings at that location."
    raise ImproperlyConfigured(msg) 

conffiles.sort()
for f in conffiles:
    execfile(os.path.abspath(f))

