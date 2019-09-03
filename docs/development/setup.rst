Setting up a dev environment
============================

Local K8s cluster
-----------------

EYRA runs in a kubernetes cluster in production. To get the development environment similar to production, it is best
to develop in a local kubernetes cluster. Two options are:

    - `MicroK8S`_
    - `Minikube`_

Preferably use microk8s, since the networking is a bit easier in that case (all pods are reachable by their IP address
from the host system, whereas minikube runs in an isolated VM).

Alternatively, you can develop on the frontend against the `staging` backend, or develop on the `backend/comic` if you
run a local postgresql database.

MicroK8S
~~~~~~~~

`<https://microk8s.io/>`_

.. code-block:: bash

    # requires snap. https://snapcraft.io/docs/installing-snapd
    $ sudo snap install microk8s --classic
    $ microk8s.start
    $ microk8s.enable dns storage helm

    # Make sure packets to/from the pod network interface can be forwarded to/from the default interface on the host via
    # the iptables tool. From https://microk8s.io/docs/
    $ sudo iptables -P FORWARD ACCEPT

    # The MicroK8s inspect command can be used to check the firewall configuration:
    $ microk8s.inspect

For interoperability with other tools. it is best to install
(`kubectl <https://kubernetes.io/docs/tasks/tools/install-kubectl/>`_) and set microk8s as a context. To get the
required configuration, run :code:`microk8s.kubectl config view --raw`, and save a either a new kubeconfig file
or merge with your existing kubeconfig file (typically set in `KUBECONFIG` env var). To activate the microk8s config you can then
run :code:`kubectl config use-context microk8s`.

Minikube
~~~~~~~~

`<https://kubernetes.io/docs/setup/minikube/>`_

Pods and services are not directly reachable through the host network, but a useful tool which can setup a network
bridge is `telepresence <https://www.telepresence.io/>`_. It allows you to 'swap out' a service running in the cluster
for a local version, running for instance in PyCharm, so that it has access to other pods/services in the cluster.

For instance, to swap out the backend run the following command:

.. code-block:: bash

   telepresence --namespace eyra-staging --swap-deployment eyra-staging-web --expose 8000 --run bash

You can start the replacement by running a local service on port 8000. All services normally available in the cluster
are then also approachable by the same hostname from your local machine
(e.g. `eyra-dev-postgresql`, `eyra-dev-redis-master`).

Installing EYRA Helm chart
--------------------------

EYRA is available as a Helm chart (which describes all services, dependencies etc). It is available from
`GitHub <https://github.com/EYRA-Benchmark/eyra-k8s>`_. You'll first need to install the
`Helm cli <https://helm.sh/>`_. Then run :code:`helm init`, which should install the cluster-side component of Helm.

Clone the EYRA k8s repository and install it:

.. code-block:: bash

    git clone https://github.com/EYRA-Benchmark/eyra-k8s.git
    cd eyra-k8s
    # setup secrets
    unzip -p eyra-chart/templates/secrets.dev.zip > eyra-chart/templates/secrets.yaml
    helm dependency update eyra-chart
    helm install ./eyra-chart --name eyra-dev -f ./eyra-chart/values.dev.yaml

This should install EYRA (takes a while). When done, you can check the following

.. code-block:: bash

    $ kubectl get svc
    NAME                           TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)     AGE
    eyra-dev-celery-flower         ClusterIP   10.152.183.217   <none>        5555/TCP    41s
    eyra-dev-docker-registry       ClusterIP   10.152.183.183   <none>        5000/TCP    41s
    eyra-dev-eyra-frontend         ClusterIP   10.152.183.53    <none>        80/TCP      41s
    eyra-dev-memcached             ClusterIP   None             <none>        11211/TCP   41s
    eyra-dev-postgresql            ClusterIP   10.152.183.221   <none>        5432/TCP    41s
    eyra-dev-postgresql-headless   ClusterIP   None             <none>        5432/TCP    41s
    eyra-dev-redis-master          ClusterIP   10.152.183.101   <none>        6379/TCP    41s
    eyra-dev-web                   ClusterIP   10.152.183.232   <none>        8000/TCP    41s
    kubernetes                     ClusterIP   10.152.183.1     <none>        443/TCP     3h7m

If the networking is setup correctly, this means you can now reach the frontend through `http://10.152.183.53`, and
the backend through `http://10.152.183.232:8000`.

By default the frontend uses the backend at `https://staging.eyrabenchmark.net`. To change it to the local backend,
enter the following:

.. code-block:: bash

    kubectl set env deploy/eyra-dev-eyra-frontend EYRA_BACKEND_URL=http://10.152.183.232:8000/api/v1
    kubectl scale --replicas=0 deploy eyra-dev-eyra-frontend
    # wait a couple of seconds
    kubectl scale --replicas=1 deploy eyra-dev-eyra-frontend

DNS setup
---------

You can use the DNS server running in the cluster. Get the IP:

.. code-block:: bash

    $ kubectl -n kube-system get pod -o wide | grep dns
    coredns-f7867546d-q4k87                           1/1     Running   0          3h9m   10.1.1.6    eslt0073   <none>
    $ echo "nameserver 10.1.1.6" > /etc/resolv.conf

Now services are reachable like this (both from the host and from inside a pod):

    - :code:`eyra-dev-eyra-frontend.default.svc.cluster.local`
    - :code:`eyra-dev-web.default.svc.cluster.local`
    - :code:`eyra-dev-postgresql.default.svc.cluster.local`

