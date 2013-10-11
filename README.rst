COMIC Django Frontend
=====================

This repository contains the Django-based web frontend for the COMIC project.  "COMIC" stands for *Consortium for Open Medical Image Computing*.

.. _installation:

Installation.
-------------

Before installing make sure you have a copy of `Django <http://www.djangoproject.com/>`_1.5 or 
newer installed.

You can fetch a copy by cloning the git repository::

    git clone git://github.com/comic/comic-django.git

Package Requirements.
---------------------

- South
- Django Countries
- Django Userena
- Django Social Auth
- PIL
- beautifulsoup4
- MatPlotLib (for rendering graphs)
- xlrd (for reading xls files)

You can install these requirements easily with pip::

    pip install South django-countries django-userena django-social-auth pil beautifulsoup4 dropbox matplotlib xlrd


Configuration.
--------------

After cloning the git repository and installing the required packages you need to change the 
database settings in ``comic/settings.py`` to your own needs. Don't forget to create the database ;)

From ``./django/`` you run::

    python manage.py syncdb

Warning::

    Fill in ``no`` when asked to create a superuser. We will do this later on.

After this is finished run::

    python manage.py migrate

Now we can create the superuser::

    python manage.py createsuperuser

Run the following to check if all permissions are correct::

    python manage.py check_permissions

When you start the server you should have a running copy of the COMIC web framework::

    python manage.py runserver

Finally login to the admin on ``localhost:8000`` and go to ``Sites``. Change ``example.com`` into::

    Domain name: localhost:8000
    Display name: localhost

If you run this in something else as the testserver, change it to your needs.

Here is a short list of urls which are useful to know:

- /admin # The admin of the framework, you can login in here with your superuser account.
- /accounts # Overview of all accounts
- /accounts/signin # Signin to an account
- /accounts/signup # Register an account
- /accounts/singout # Signout the current user

Troubleshooting.
-----------------
- Pip does not install matplotlib correctly -> You can try an installer from the matplotlib website: http://matplotlib.org/downloads.html