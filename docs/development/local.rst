Local K8S cluster
-----------------

The recommended way of doing development is by running EYRA on a local kubernetes cluster through
`minikube <https://kubernetes.io/docs/setup/minikube/>`_. It is then possible to 'swap out' a service running
in the cluster with a local version running for instance in PyCharm using
`telepresence <https://www.telepresence.io/>`_.

For instance, to swap out the backend run the following command:

.. code-block:: bash

   telepresence --namespace eyra-staging --swap-deployment eyra-staging-web --expose 8000 --run bash

You can start the replacement by running a local service on port 8000. All services normally available in the cluster
are then also approachable by the same hostname from your local machine
(e.g. `eyra-staging-postgresql`, `eyra-staging-redis-master`).