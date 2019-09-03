Building these docs
===================

- Install dependencies from :code:`requirements.dev.txt` and :code:`requirements.txt`.

- When developing, you can use :code:`sphinx-autobuild` to get an development server that automatically refreshes on
  changes:


.. code-block:: bash

    # Auto reload dev server:
    sphinx-autobuild docs docs/_build/html

- To make a 'production' build of the docs, run :code:`make` from the :code:`docs/` folder. This will
  generate a html based structure in :code:`docs/_build/html`.

.. code-block:: bash

    # Build docs to docs/_build/html
    cd docs && make
