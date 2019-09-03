Local K8S cluster
-----------------

The recommended way of doing development is by running EYRA on a local kubernetes cluster through
`microk8s <https://microk8s.io/>`_ or `minikube <https://kubernetes.io/docs/setup/minikube/>`_.

Preferably use microk8s, since the networking is a bit easier in that case (all pods are reachable by their IP address
from the host system, whereas minikube runs in an isolated VM).

MicroK8S
========

.. code-block:: bash

    # requires snap. https://snapcraft.io/docs/installing-snapd
    sudo snap install microk8s --classic
    microk8s.start
    microk8s.enable dns dashboard ingress helm

    # Make sure packets to/from the pod network interface can be forwarded to/from the default interface on the host via
    # the iptables tool. From https://microk8s.io/docs/
    sudo iptables -P FORWARD ACCEPT

    # The MicroK8s inspect command can be used to check the firewall configuration:
    microk8s.inspect

For interoperability with other tools. it is best to install
(`kubectl <https://kubernetes.io/docs/tasks/tools/install-kubectl/>`_) and set microk8s as a context. To get the
required configuration, run :code:`microk8s.kubectl config view --raw`, and save a either a new kubeconfig file
or merge with your existing kubeconfig file (typically set in $KUBECONFIG). To activate the microk8s config you can then
run :code:`kubectl config use-context microk8s`.

Minikube
========
Pods and services are not directly reachable through the host network, but a useful tool which can setup a network
bridge is `telepresence <https://www.telepresence.io/>`_. It allows you to 'swap out' a service running in the cluster
for a local version, running for instance in PyCharm, so that it has access to other pods/services in the cluster.

For instance, to swap out the backend run the following command:

.. code-block:: bash

   telepresence --namespace eyra-staging --swap-deployment eyra-staging-web --expose 8000 --run bash

You can start the replacement by running a local service on port 8000. All services normally available in the cluster
are then also approachable by the same hostname from your local machine
(e.g. `eyra-staging-postgresql`, `eyra-staging-redis-master`).

Installing EYRA Helm chart
==========================

EYRA is available as a Helm chart (which describes all services, dependencies etc). It is available from
`GitHub <https://github.com/EYRA-Benchmark/eyra-k8s>`_. You'll first need to install the
`Helm cli <https://helm.sh/>`_. Then run :code:`helm init`, which should install the cluster-side component of Helm.

Then clone the EYRA k8s repository and install it:

.. code-block:: bash

    git clone https://github.com/EYRA-Benchmark/eyra-k8s.git
    cd eyra-k8s
    # setup secrets
    unzip -p eyra-chart/templates/secrets.dev.zip > eyra-chart/templates/secrets.yaml
    helm install ./eyra-chart --name eyra-dev -f ./eyra-chart/values.dev.yaml