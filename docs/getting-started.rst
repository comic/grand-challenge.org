===============
Getting Started
===============

Grand-challenge is distributed as a set of containers that are defined and linked together in ``docker-compose.yml``. 
To develop the platform you need to have docker and docker-compose running on your system.

Installation
------------

1. Download and install Docker

    *Linux*: Docker_ and `Docker Compose`_

    *Windows 10 Pro (Build 15063 or later)*: `Docker for Windows`_

    *Older Windows versions*: `Docker Toolbox`_

2. Clone the repo

.. code-block:: console

    $ git clone https://github.com/comic/grand-challenge.org
    $ cd grand-challenge.org

3. You can then start the site by invoking

.. code-block:: console

    $ ./cycle_docker_compose.sh

You can then navigate to https://gc.localhost in your browser to see the development site,
this is using a self-signed certificate so you will need to accept the security warning.
The ``app/`` directory is mounted in the containers,
``werkzeug`` handles the file monitoring and will restart the process if any changes are detected.
If you need to manually restart the process you can do this when running ``cycle_docker_compose.sh`` by pressing  ``CTRL+D`` in the console window,
you can also kill the server with ``CTRL+C``.

Windows
~~~~~~~

Running Grand-Challenge within a Windows environment requires additional steps before invoking the ``cycle_docker_compose.sh`` script.

1. Install ``Make`` for an available ``bash`` console
2. Set an environment variable to enable Windows path conversions for Docker

.. code-block:: console 

    $ export COMPOSE_CONVERT_WINDOWS_PATHS=1

3. Add the following line to your hosts file (``C:\Windows\System32\drivers\etc\hosts``)

.. code-block:: console

    # Using Docker for Windows:
    127.0.0.1 gc.localhost

    # Using Docker Toolbox:
    192.168.99.100 gc.localhost


4. Share the drive where this repository is located with Docker

    *Docker for Windows*

        1. Right-click Docker icon in taskbar and click "Settings"
        2. Go to "Shared drives" tab
        3. Mark the checkbox of the drive where this repository is located

    *Docker Toolbox*

        1. Open VirtualBox
        2. Go to the virtual machine that belongs to docker
        3. Double click "Shared folders"
        4. Click on the "Add New Shared Folder" button on the right
        5. In the Folder Path box, type the drive letter where this repository is located (eg. ``C:\``)
        6. In the Folder Name box, type the drive letter lowercased (eg. ``c``)
        7. Restart the docker machine by typing ``docker-machine restart`` in your console
        8. SSH into the docker VM with ``docker-machine ssh``
        9. Append the following lines to the file ``/mnt/sda1/var/lib/boot2docker/profile``

.. code-block:: console

    mkdir /home/docker/c # Change the 'c' to your drive letter
    sudo mount -t vboxsf -o uid=1000,gid=50 c /home/docker/c # Again, change both 'c's to your drive letter



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
2. Then select the docker server (usually the unix socket)
3. Set the service to ``web``
4. Click ``OK``
5. Set the path mappings from ``<Project root>/app->/app``
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
15. Install the ``Flake8 Support`` plugin so that PyCharm will understand ``noqa`` comments

It is also recommended to install the black extension (version ``19.10b0``) for code formatting.

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

6. Run migrations and check_permissions (optionally load demo data).

.. code-block:: console

    $ cd app
    $ python manage.py migrate
    $ python manage.py check_permissions
    $ python manage.py init_gc_demo

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

Using docker
~~~~~~~~~~~~

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
3. Removing the users that are created by ``init_gc_demo``

.. _Docker: https://docs.docker.com/install/
.. _`Docker Compose`: https://docs.docker.com/compose/install/
.. _`Docker for Windows`: https://docs.docker.com/docker-for-windows/install/
.. _`Docker Toolbox`: https://docs.docker.com/toolbox/toolbox_install_windows/
