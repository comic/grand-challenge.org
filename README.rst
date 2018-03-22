grand-challenge.org
===================

.. image:: https://travis-ci.org/comic/grand-challenge.org.svg?branch=master
   :target: https://travis-ci.org/comic/grand-challenge.org
.. image:: https://api.codeclimate.com/v1/badges/b056e3bb28f145fa1bde/maintainability
   :target: https://codeclimate.com/github/comic/grand-challenge.org/maintainability
   :alt: Maintainability
.. image:: https://codecov.io/gh/comic/grand-challenge.org/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/comic/grand-challenge.org
.. image:: https://readthedocs.org/projects/grand-challengeorg/badge/?version=latest
   :target: http://grand-challengeorg.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

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
`the docs <http://grand-challengeorg.readthedocs.io>`_
