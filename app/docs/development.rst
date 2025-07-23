===========
Development
===========

Grand-challenge is distributed as a set of containers that are defined and linked together in ``docker-compose.yml``.
To develop the platform you need to have docker and docker compose running on your system.

Installation
------------

1. Download and install Docker

    *Linux*: Docker_ and `Docker Compose`_

    *Windows*: `WSL2`_, `Docker Desktop for Windows`_ with the `Docker Desktop WSL2 Backend`_ and `Docker Compose`_

*Note for Windows Users*: we **only** support development using Windows 10 and WSL2.
Please ensure that the correct backend is enabled in your docker settings, and run all of the following commands in the ``wsl`` shell.
At the time of writing, we use ``Ubuntu 20.04`` from the Microsoft store as the default distro.
As WSL2 is slow at syncing files between Windows and WSL2 filesystems it is best to checkout the codebase within ``wsl`` itself.

The docker compose cycle script below utilizes `Docker Buildx`_. Depending on the steps above, buildx should be
installed alongside docker. If the docker compose cycle invocation below crashes on buildx, it is recommended to
(re)install the latest version.

2. Clone the repo

.. code-block:: console

    $ git clone https://github.com/comic/grand-challenge.org
    $ cd grand-challenge.org

3. Set your local docker group id in your ``.env`` file

.. code-block:: console

    $ echo DOCKER_GID=`getent group docker | cut -d: -f3` > .env

4. You can then start the development site by invoking

.. code-block:: console

    $ make runserver

The ``app/`` directory is mounted in the containers,
``werkzeug`` handles the file monitoring and will restart the process if any changes are detected.
You can also kill the server with ``CTRL+C``.

The Development Site
~~~~~~~~~~~~~~~~~~~~

If you follow the installation instructions above you will be able to go to https://gc.localhost to see the development site,
this is using a self-signed certificate so you will need to accept the security warning.

The development site will apply all migrations and add a set of fixtures to help you with developing grand-challenge.org.
These fixtures include Archives, Reader Studies, Challenges, Algorithms and Workstations.
Some default users are created with specific permissions, each user has the same username and password.
These users include ``archive``, ``readerstudy``, ``demo``, ``algorithm`` and ``workstation``,
who have permission to administer the existing fixtures and create new ones.

If you would like to test out the algorithms you can create a simple algorithm that lists its inputs in a `results.json` file by running

.. code-block:: console

    $ make algorithm_evaluation_fixtures

Before you run

.. code-block:: console

    $ make runserver



There is an interactive debugger from ``django-extensions`` which will halt on exceptions (see the `RunServerPlus`_ documentation),
it's really handy for interactive debugging to place ``1/0`` in your code as a breakpoint.

Running the Tests
-----------------

GitHub actions is used to run the test suite on every new commit.
You can also run the tests locally by

1. In a console window make sure the database is running

.. code-block:: console

    $ make runserver

2. Then in a second window run

.. code-block:: console

    $ docker compose run --rm celery_worker pytest -n 2

Replace 2 with the number of CPUs that you have on your system, this runs
the tests in parallel.

If you want to add a new test please add them to the ``app/tests`` folder.
If you only want to run the tests for a particular app, eg. for ``teams``, you can do

.. code-block:: console

    $ docker compose run --rm celery_worker pytest -k teams_tests

Development
-----------

You will need to install pre-commit so that the code is correctly formatted

.. code-block:: console

    $ python3 -m pip install pre-commit

Please do all development on a branch and make a pull request to main, this will need to be reviewed before it is integrated.

We recommend using Pycharm for development.

Running through docker compose
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You will need the Professional edition to use the docker compose integration.
To set up the environment in Pycharm Professional 2018.1:

1. ``File`` -> ``Settings`` -> ``Project: grand-challenge.org`` -> ``Project Interpreter`` -> ``Cog`` wheel (top right) -> ``Add`` -> ``Docker Compose``
2. Then select the docker server (usually the unix socket, or Docker for Windows)
3. Set the service to ``web``
4. Click ``OK``
5. Set the path mappings:

   1. Local path: ``<Project root>/app``
   2. Remote path: ``/app``

6. Click ``OK``

Pycharm will then spend some time indexing the packages within the container to help with code completion and inspections.
If you edit any files these will be updated on the fly by werkzeug.

PyCharm Configuration
~~~~~~~~~~~~~~~~~~~~~

It is recommended to setup django integration to ensure that the code completion, tests and import optimisation works.

1. Open ``File`` -> ``Settings`` -> ``Languages and Frameworks`` -> ``Django``
2. Check the ``Enable Django Support`` checkbox
3. Set the project root to ``<Project root>/app``
4. Set the settings to ``config/settings.py``
5. Check the ``Do not use the django test runner`` checkbox
6. In the settings window navigate to ``Tools`` -> ``Python integrated tools``
7. Under the testing section select ``pytest`` as the default test runner
8. Under the Docstrings section set ``NumPy`` as the docstrings format
9. In the settings window navigate to ``Editor`` -> ``Code Style``
10. Click on the ``Formatter Control`` tab and enable ``Enable formatter markers in comments``
11. In the settings window navigate to ``Editor`` -> ``Code Style`` -> ``Python``
12. On the ``Wrapping and Braces`` tab set ``Hard wrap at`` to ``86`` and ``Visual guide`` to ``79``
13. On the ``Imports`` tab enable ``Sort Import Statements``, ``Sort imported names in "from" imports``, and ``Sort plain and "from" imports separately in the same group``
14. Click ``OK``
15. Install the ``Flake8 Support`` plugin so that PyCharm will understand ``noqa`` comments. At the time of writing, the plugin is not compatible with PyCharm 2020. You can still install Flake8 as an external tool though. To do so, follow these steps:

    1. Install flake8 ``pip install flake8``
    2. In PyCharm, in the settings window navigate to ``Tools`` -> ``External Tools`` and add a new one with the following configuration:

       1. Program: file path to ``flake8.exe`` you just installed
       2. Arguments: ``$FilePath$``
       3. Working directory: ``$ProjectFileDir$``

16. In the main window at the top right click the drop down box and then click ``Edit Configurations...``
17. Click on ``templates`` -> ``Python Tests`` -> ``pytest``, and enter ``--reuse-db`` in the ``Additional Arguments`` box and ``run --rm`` in the ``Command and options`` box under ``Docker Compose``

It is also recommended to install the black extension for code formatting. You can add it as an external tool, following the same instructions as for ``Flake8`` above.

Creating Migrations
-------------------

If you change a ``models.py`` file then you will need to make the corresponding migration files.
You can do this with

.. code-block:: console

    $ make migrations

or, more explicitly

.. code-block:: console

    $ docker compose run --rm --user `id -u` web python manage.py makemigrations


add these to git and commit.

Building the documentation
--------------------------

Having built the web container with ``make runserver`` you can use this to generate the docs with

.. code-block:: console

    $ make docs

This will create the docs in the ``docs/_build/html`` directory.


Adding new dependencies
-----------------------

`uv` is used to manage the dependencies of the platform.
To add a new dependency use

.. code-block:: console

    $ uv add <whatever>

and then commit the ``pyproject.toml`` and ``uv.lock``.
If this is a development dependency then use the ``--dev`` flag, see the ``uv`` documentation for more details.

Versions are unpinned in the ``pyproject.toml`` file, to update the resolved dependencies use

.. code-block:: console

    $ uv lock --upgrade-package <whatever>

and commit the updated ``uv.lock``.

The containers will need to be rebuilt after running these steps, so stop the ``make runserver`` process with ``CTRL+C`` and restart.

Frontend Asset Management
-------------------------

This project uses `webpack <https://webpack.js.org/>`_ to manage frontend assets like JavaScript and CSS. This allows us to use modern JavaScript features, manage dependencies through ``npm``, and bundle our assets for production.

The main configuration file for this process is ``webpack.config.js`` located in the ``/app/`` directory so all ``npm`` commands below need to be ran from that directory.

Key Concepts
~~~~~~~~~~~~

*   **Entry Points**: Each entry in the ``entry`` object in ``webpack.config.js`` corresponds to a "bundle". A bundle is a set of output files (JS and CSS) that can be included in a template or widget.
*   **Bundling**: Webpack takes the entry point, finds all its dependencies (other JS/CSS files it imports), and bundles them into a single JS file and a single CSS file.
*   **Output**: The bundled files are placed in ``/app/grandchallenge/core/static/npm_vendored/``. In development filenames include a content hash for cache-busting (e.g., ``jquery-a1b2c3d4.js``), in production this is not needed.
*   **Stats File**: ``webpack-bundle-tracker`` generates a ``webpack-stats.json`` file in the output directory. This file maps bundle names to their generated, hashed filenames.
*   **Django Integration**: ``django-webpack-loader`` reads the ``webpack-stats.json`` file and provides a template tag (``render_bundle``) to easily include the correct, hashed asset files in Django templates.

How to Add a JavaScript Dependency
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add a 3rd-party library (from npm)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you need to use a library like ``htmx`` or ``d3``, you can add it as a separate bundle.

1.  **Install the package**:

    .. code-block:: bash

        npm install htmx.org

2.  **Add an entry point in ``webpack.config.js``**:
    Open ``/app/webpack.config.js`` and add a new entry to the ``entry`` object. The key is the name you'll use to refer to this bundle, and the value is the package name.

    .. code-block:: javascript

        // webpack.config.js
        module.exports = {
          entry: {
            'jquery': 'jquery',
            'htmx': 'htmx.org', // <-- Add this line
            'jsoneditor_widget': './grandchallenge/core/javascript/jsoneditor_widget.mjs',
            'sentry': './grandchallenge/core/javascript/sentry.mjs',
          },
          // ...
        };

3.  **Include the bundle in a template**:
    See the "Using Bundles" section below.

Add a custom JavaScript file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For your own custom JavaScript code, follow these steps:

1.  **Create your JavaScript file**:
    Create a new file in ``/app/grandchallenge/core/javascript/``. For example, ``my_new_feature.mjs``. You can import any npm packages or other custom modules within this file.

    .. code-block:: javascript

        // /app/grandchallenge/core/javascript/my_new_feature.mjs
        import $ from 'jquery';

        console.log("My new feature is loaded!");
        // Your code here...

2.  **Add an entry point in ``webpack.config.js``**:
    Add your new file as an entry point. The key is the bundle name, and the value is the path to your file.

    .. code-block:: javascript

        // webpack.config.js
        module.exports = {
          entry: {
            'jquery': 'jquery',
            'jsoneditor_widget': './grandchallenge/core/javascript/jsoneditor_widget.mjs',
            'sentry': './grandchallenge/core/javascript/sentry.mjs',
            'my_new_feature': './grandchallenge/core/javascript/my_new_feature.mjs', // <-- Add this line
          },
          // ...
        };

3.  **Include the bundle**:
    See the "Using Bundles" section below.

Using Bundles
~~~~~~~~~~~~~

Once you've defined a bundle in ``webpack.config.js`` and run the webpack build, you can include it in your Django templates or widgets.

In Django Templates
^^^^^^^^^^^^^^^^^^^

To include a bundle directly in a template:

1.  **Load the template tag**:
    At the top of your template, add ``{% load render_bundle from webpack_loader %}``.

2.  **Render the bundle**:
    Use the ``render_bundle`` tag where you want to include the ``<script>`` and ``<link>`` tags. The first argument is the bundle name (from your ``webpack.config.js`` entry key), and the second is the file type ('js' or 'css').

    .. code-block:: html

        {# my_template.html #}
        {% load render_bundle from webpack_loader %}

        ...

        {% block extra_js %}
          {% render_bundle 'my_new_feature' 'js' %}
          {% render_bundle 'my_new_feature' 'css' %}
        {% endblock %}

    This will render the appropriate ``<script>`` and ``<link>`` tags with the correct hashed filenames.

In Django Widgets
^^^^^^^^^^^^^^^^^^

To associate a JavaScript bundle with a Django widget:

1.  **Inherit from ``WebpackWidgetMixin``**:
    Your widget class in ``widgets.py`` should inherit from ``grandchallenge.core.utils.webpack.WebpackWidgetMixin``.

2.  **Define ``webpack_bundles``**:
    Add a class attribute ``webpack_bundles`` to your widget. This should be a list of strings, where each string is a bundle name from your ``webpack.config.js``.

    **Example from ``/app/grandchallenge/core/widgets.py``**:

    .. code-block:: python

        from grandchallenge.core.utils.webpack import WebpackWidgetMixin

        class MyWidget(WebpackWidgetMixin, forms.Textarea):
            template_name = "my_app/my_widget.html"
            webpack_bundles = ["my_new_feature"] # <-- Associate the bundle

            # ... rest of your widget code

    The ``WebpackWidgetMixin`` automatically adds the necessary JS and CSS files for the specified bundles to the form's media.

Development and Production
~~~~~~~~~~~~~~~~~~~~~~~~~~

*   **Development**: Run ``npm run dev`` or ``npm run watch``. This creates bundles with source maps for easier debugging.
*   **Production**: The build process in the container will run ``npm run build``, which creates minified, production-ready assets.

The ``webpack.config.js`` file uses the ``NODE_ENV`` environment variable to determine which build to perform.

Going to Production
-------------------

The docker compose file included here is for development only.
If you want to run this in a production environment you will need to make several changes, not limited to:

1. Use ``gunicorn`` rather than run ``runserver_plus`` to run the web process
2. `Disable mounting of the docker socket <https://docs.docker.com/engine/security/https/>`_
3. Removing the users that are created by ``development_fixtures``

.. _Docker: https://docs.docker.com/install/
.. _`Docker Compose`: https://docs.docker.com/compose/install/
.. _`WSL2`: https://docs.microsoft.com/en-us/windows/wsl/install-win10/
.. _`Docker Desktop for Windows`: https://docs.docker.com/docker-for-windows/install/
.. _`Docker Desktop WSL2 Backend`: https://docs.docker.com/docker-for-windows/wsl/
.. _`Docker Buildx`: https://docs.docker.com/buildx/working-with-buildx/#install
.. _`RunServerPlus`: https://django-extensions.readthedocs.io/en/latest/runserver_plus.html
.. _`Running WSL GUI Apps on Windows 10`: https://techcommunity.microsoft.com/t5/windows-dev-appconsult/running-wsl-gui-apps-on-windows-10/ba-p/1493242
