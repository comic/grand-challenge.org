===============
Getting Started
===============

Grand-challenge is distributed as a set of containers that are defined and linked together in ``docker-compose.yml``. 
To develop the platform you need to have docker and docker-compose running on your system.

Installation
------------

1. Install Docker_ and `Docker Compose`_ 
2. Clone the repo

.. code-block:: console

    $ git clone https://github.com/comic/grand-challenge.org
    $ cd grand-challenge.org

3. You can then start the site by invoking 

.. code-block:: console

    $ ./cycle_docker_compose.sh

You can then navigate to https://localhost in your browser to see the development site, 
this is using a self-signed certificate so you will need to accept the security warning.
The ``app/`` directory is mounted in the containers, so if you make any changes to the code you will need to restart the processes.
You can do this when running ``cycle_docker_compose.sh`` by pressing  ``CTRL+D`` in the console window, 
you can also kill the server with ``CTRL+C``.

Windows
```````

Running Grand-Challenge within a Windows environment requires additional steps before invoking the ``cycle_docker_compose.sh`` script.

1. Install ``Make`` for an available ``bash`` console
2. Set an environment variable to enable Windows path conversions for Docker

.. code-block:: console 

	$ export COMPOSE_CONVERT_WINDOWS_PATHS=1


Running the Tests
-----------------

TravisCI_ is used to run the test suite on every new commit. 
You can also run the tests locally by 

1. In a console window make sure the database is running

.. code-block:: console
    
    $ ./cycle_docker_compose.sh

2. Then in a second window run

.. code-block:: console

    $ docker-compose run --rm web pytest

If you want to add a new test please add them to the ``app/tests`` folder.
If you only want to run the tests for a particular app, eg. for `teams`, you can do

.. code-block:: console

    $ docker-compose run --rm web pytest -k teams_tests


Development
-----------

You will need to install pre-commit so that the code is correctly formatted

.. code-block:: console

    $ python3 -m pip install pre-commit

We recommend using Pycharm for development.
You will need the Professional edition to use the docker-compose integration. 
To set up the environment in Pycharm Professional 2018.1:

1. File -> Settings -> Project: grand-challenge.org -> Project Interpreter -> Cog wheel (top right) -> Add -> Docker Compose
2. Then select the docker server (usually the unix socket)
3. Set the service to ``web``
4. Click OK in both windows

Pycharm will then spend some time indexing the packages within the container to help with code completion and inspections.
If you edit any template files these will be updated on the fly. 
If you edit any ``.py``, ``.css``, ``.js`` (etc) you will need to restart the processes using ``CTRL+D`` with ``cycle_docker_compose.sh``.
You can then add ``py.test`` test configurations to run the tests from within Pycharm.

Please do all development on a branch and make a pull request to master, this will need to be reviewed before it is integrated.

Creating Migrations
-------------------

If you change a ``models.py`` file then you will need to make the corresponding migration files.
You can do this with

.. code-block:: console

    $ docker-compose run --rm --user `id -u` web python manage.py makemigrations


add these to git and commit.


Building the docs
-----------------

To build the docs you need to install the environment on your local machine, we use pipenv for this.

1. Install pipenv

.. code-block:: console

    $ pip install pipenv

2. Install the environment from the root of the ``grand-challenge.org`` repo  with

.. code-block:: console

    $ pipenv install

3. You can then launch a shell in this newly created environment to build the docs

.. code-block:: console

    $ pipenv shell
    $ cd docs
    $ make html

This will create the docs in the ``docs/_build/html`` directory.


Adding new dependencies
-----------------------

Pipenv is used to manage the dependencies of the platform. 
To add a new dependency use

.. code-block:: console

    $ pipenv install <whatever>

and then commit the ``Pipfile`` and ``Pipfile.lock``. 
If this is a development dependency then use the ``--dev`` flag, see the ``pipenv`` documentation for more details.

Versions are unpinned in the ``Pipfile``, to update the resolved dependencies use

.. code-block:: console

    $ pipenv update

and commit the update ``Pipfile.lock``. 
The containers will need to be rebuilt after running these steps, so stop the ``cycle_docker_compose.sh`` process with ``CTRL+C`` and restart.


.. _TravisCI: https://travis-ci.org/comic/grand-challenge.org
.. _Docker: https://docs.docker.com/install/
.. _`Docker Compose`: https://docs.docker.com/compose/install/

