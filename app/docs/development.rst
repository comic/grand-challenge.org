===========
Development
===========

Grand-challenge is distributed as a set of containers that are defined and linked together in ``docker-compose.yml``.
To develop the platform you need to have docker and docker-compose running on your system.

Installation
------------

1. Download and install Docker

    *Linux*: Docker_ and `Docker Compose`_

    *Windows*: `WSL2`_, `Docker Desktop for Windows`_ with the `Docker Desktop WSL2 Backend`_ and `Docker Compose`_

*Note for Windows Users*: we **only** support development using Windows 10 and WSL2.
Please ensure that the correct backend is enabled in your docker settings, and run all of the following commands in the ``wsl`` shell.
At the time of writing, we use ``Ubuntu 20.04`` from the Microsoft store as the default distro.
As WSL2 is slow at syncing files between Windows and WSL2 filesystems it is best to checkout the codebase within ``wsl`` itself.

The docker-compose cycle script below utilizes `Docker Buildx`_. Depending on the steps above, buildx should be
installed alongside docker. If the docker-compose cycle invocation below crashes on buildx, it is recommended to
(re)install the latest version.

2. Clone the repo

.. code-block:: console

    $ git clone https://github.com/comic/grand-challenge.org
    $ cd grand-challenge.org

3. You can then start the development site by invoking

.. code-block:: console

    $ ./cycle_docker_compose.sh

The ``app/`` directory is mounted in the containers,
``werkzeug`` handles the file monitoring and will restart the process if any changes are detected.
If you need to manually restart the process you can do this when running ``cycle_docker_compose.sh`` by pressing  ``CTRL+D`` in the console window,
you can also kill the server with ``CTRL+C``.

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

    $ make create_io_algorithm

Before you run

.. code-block:: console

    $ ./cycle_docker_compose.sh


You can also download an `Example Algorithm Image`_ from Docker Hub.
Save it locally with

.. code-block:: console

    $ docker pull grandchallenge/otsu
    $ docker save grandchallenge/otsu > otsu.tar

You can then upload ``otsu.tar`` as a container image to the local site.

If you would like to generate your own Algorithm or Evaluation containers you can do this using `Evalutils`_,
please see the `Getting Started with Evalutils`_ documentation.

There is an interactive debugger from ``django-extensions`` which will halt on exceptions (see the `RunServerPlus`_ documentation),
it's really handy for interactive debugging to place ``1/0`` in your code as a breakpoint.

Running the Tests
-----------------

GitHub actions is used to run the test suite on every new commit.
You can also run the tests locally by

1. In a console window make sure the database is running

.. code-block:: console

    $ ./cycle_docker_compose.sh

2. Then in a second window run

.. code-block:: console

    $ docker-compose run --rm web pytest -n 2

Replace 2 with the number of CPUs that you have on your system, this runs
the tests in parallel.

If you want to add a new test please add them to the ``app/tests`` folder.
If you only want to run the tests for a particular app, eg. for ``teams``, you can do

.. code-block:: console

    $ docker-compose run --rm web pytest -k teams_tests

Development
-----------

You will need to install pre-commit so that the code is correctly formatted

.. code-block:: console

    $ python3 -m pip install pre-commit

Please do all development on a branch and make a pull request to master, this will need to be reviewed before it is integrated.

We recommend using Pycharm for development.

Running through docker-compose
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You will need the Professional edition to use the docker-compose integration.
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

It is also recommended to install the black extension (version ``19.10b0``) for code formatting. You can add it as an external tool, following the same instructions as for ``Flake8`` above.

Running locally
~~~~~~~~~~~~~~~
Alternatively, it can be useful to run code from a local python environment - this allows for easier debugging and does
not require e.g. the professional edition of PyCharm. The setup described here uses all services from the normal
``docker-compose`` stack, except for the web service. Though this service is running, a separate Django dev server is
started in PyCharm (or from the terminal). As the dev server is running on port ``8000`` by default, there is no port conflict
with the service running in the docker container.

1. Run the ``docker-compose`` stack for the database and celery task handling

.. code-block:: console

    $ ./cycle_docker_compose.sh

2. Make sure you have ``poetry`` installed.
3. In a new terminal, create a new virtual python environment using ``poetry install`` in this repository's root folder.
4. Activate the virtual env: ``poetry shell``.
5. Load the environmental variables contained in ``.env.local``

.. code-block:: console

    $ export $(cat .env.local | egrep -v "^#" | xargs)

6. Run migrations (optionally load demo data).

.. code-block:: console

    $ cd app
    $ python manage.py migrate
    $ python manage.py runscript development_fixtures

7. You can now start the server using ``python manage.py runserver_plus``.

8. To setup PyCharm:

   1. ``File`` -> ``Settings`` -> ``Project: grand-challenge.org`` -> ``Project Interpreter`` -> Select your created virtual environment
   2. For each run/debug configuration, make sure the environmental variables are loaded,
      the easiest is to use `this plugin <https://plugins.jetbrains.com/plugin/7861-envfile>`_. Or they can be pasted after pressing
      the folder icon in the ``Environmental variables`` field.
   3. Useful to setup: the built-in python/django console in Pycharm:
      ``Settings`` -> ``Build``, ``execution``, ``deployment`` -> ``Console`` -> Python/Django console.
      Choose the same python interpreter here, and make sure to load the environmental variables
      (the .env plugin cannot be used here, the variables can only be pasted).

Creating Migrations
-------------------

If you change a ``models.py`` file then you will need to make the corresponding migration files.
You can do this with

.. code-block:: console

    $ make migrations

or, more explicitly

.. code-block:: console

    $ docker-compose run --rm --user `id -u` web python manage.py makemigrations


add these to git and commit.

Building the documentation
--------------------------

Having built the web container with ``cycle_docker_compose.sh`` you can use this to generate the docs with

.. code-block:: console

    $ make docs

This will create the docs in the ``docs/_build/html`` directory.


Adding new dependencies
-----------------------

Poetry is used to manage the dependencies of the platform.
To add a new dependency use

.. code-block:: console

    $ poetry add <whatever>

and then commit the ``pyproject.toml`` and ``poetry.lock``.
If this is a development dependency then use the ``--dev`` flag, see the ``poetry`` documentation for more details.

Versions are unpinned in the ``pyproject.toml`` file, to update the resolved dependencies use

.. code-block:: console

    $ poetry lock

and commit the update ``poetry.lock``.
The containers will need to be rebuilt after running these steps, so stop the ``cycle_docker_compose.sh`` process with ``CTRL+C`` and restart.

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
.. _`Example Algorithm Image`: https://hub.docker.com/r/grandchallenge/otsu
.. _`Evalutils`: https://pypi.org/project/evalutils/
.. _`Getting Started with Evalutils`: https://evalutils.readthedocs.io/en/latest/usage.html#getting-started
