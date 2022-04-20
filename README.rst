grand-challenge.org
===================

.. image:: https://github.com/comic/grand-challenge.org/workflows/CI/badge.svg
   :target: https://github.com/comic/grand-challenge.org/actions?query=workflow%3ACI+branch%3Amain
   :alt: Build Status
.. image:: https://codecov.io/gh/comic/grand-challenge.org/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/comic/grand-challenge.org
   :alt: Code Coverage Status
.. image:: https://img.shields.io/badge/docs-published-success
   :target: https://comic.github.io/grand-challenge.org/
   :alt: Documentation
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/ambv/black
   :alt: Black Code Style
.. image:: https://zenodo.org/badge/4557968.svg
   :target: https://zenodo.org/badge/latestdoi/4557968
   :alt: Cite Us with Zenodo

Fair and objective comparisons of machine learning algorithms improves the
quality of research outputs in both academia and industry. This repo
contains the source code behind
`grand-challenge.org <https://grand-challenge.org>`_, which serves as a
resource for users to compare algorithms in biomedical image analysis. This
instance is maintained by developers at Radboud University Medical Center
in Nijmegen, The Netherlands and Fraunhofer MeVis in Bremen, Germany, but
you can also create your own instance.

This django powered website has been developed by the Consortium for Open
Medical Image Computing. It features:
   * Creation and management of challenges
   * Easy creation of challenge sites with WYSIWYG editing
   * Fine grained permissions for challenge administrators and participants
   * Management and serving of datasets
   * Automated evaluation of predictions
   * Live leaderboards
   * User profiles and social authentication
   * Teams

If you would like to start your own website, or contribute to the development
of the framework, please see
`the docs <https://comic.github.io/grand-challenge.org/>`_
