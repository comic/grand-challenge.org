import os

from kubernetes.config import load_incluster_config, load_kube_config, incluster_config as kubernetes_config
from kubernetes import client
from kubernetes.client.rest import ApiException

from django.conf import settings

from comic.eyra_algorithms.models import Job

# override service token mounts when running with telepresence
if settings.K8S_USE_CLUSTER_CONFIG:
    kubernetes_config.SERVICE_TOKEN_FILENAME = \
        os.environ.get('TELEPRESENCE_ROOT', '') + kubernetes_config.SERVICE_TOKEN_FILENAME
    kubernetes_config.SERVICE_CERT_FILENAME = \
        os.environ.get('TELEPRESENCE_ROOT', '') + kubernetes_config.SERVICE_CERT_FILENAME

# the capacity of the PVC volume used for in/output.
IO_PVC_CAPACITY = '50Gi'

# https://github.com/s3tools/s3cmd
# used for up- & downloading data from s3
# s3cmd_prefix = f"""
# s3cmd --access_key={settings.AWS_ACCESS_KEY_ID}\
#  --secret_key={settings.AWS_SECRET_ACCESS_KEY}\
#  --host={settings.AWS_S3_HOST}\
#  --host-bucket="%(bucket).{settings.AWS_S3_HOST}" """
s3cmd_prefix = f"s3cmd --region={settings.AWS_S3_REGION_NAME}"


# Use on Eyra Job, executes job on K8S cluster
class K8sJob(object):
    def __init__(self, job: Job, namespace: str=os.environ.get('K8S_NAMESPACE')):
        self.job = job
        self.namespace = namespace
        self.io_pvc = None

    def load_kubeconfig(self):
        if settings.K8S_USE_CLUSTER_CONFIG:
            load_incluster_config()
        else:
            load_kube_config()

    def io_pvc_name(self):
        return f'pvc-job-{self.job.pk}'

    def job_name(self):
        return f'job-{self.job.pk}'

    # create persistent volume claim for IO (data input/output)
    def create_io_pvc(self):
        self.io_pvc = client.CoreV1Api().create_namespaced_persistent_volume_claim(
            os.environ.get('K8S_NAMESPACE'),
            client.V1PersistentVolumeClaim(
                metadata=client.V1ObjectMeta(name=self.io_pvc_name()),
                spec=client.V1PersistentVolumeClaimSpec(
                    access_modes=['ReadWriteOnce'],
                    resources=client.V1ResourceRequirements(requests={'storage': IO_PVC_CAPACITY})
                )
            )
        )
        return self.io_pvc

    # the sh script that runs in the init container (downloads input data from S3)
    def input_script(self):
        s3cmd = "\n".join([
            f"{s3cmd_prefix} get s3://{settings.AWS_STORAGE_BUCKET_NAME}/data_files/{data_file_pk} /data/input/{input_name}"
            for input_name, data_file_pk in self.job.input_name_data_file_pk_map().items()
        ])

        return f"""
set -e
echo "Preparing data volume..."
mkdir /data/input
pip install s3cmd --quiet
{s3cmd}
echo "done"
"""

    # the sh script that runs in the init container (uploads output data to S3)
    def output_script(self):
        s3cmd = f"{s3cmd_prefix} put /data/output s3://{settings.AWS_STORAGE_BUCKET_NAME}/data_files/{self.job.output.pk}"
        return f"""
set -e
echo "Uploading output data..."
pip install s3cmd --quiet
{s3cmd}
echo "Done"
"""

    # run this job on K8S. Does not wait for completion
    def run(self):
        self.load_kubeconfig()
        self.create_io_pvc()

        input_container = client.V1Container(
            name=f"input",
            image='python:2-alpine',
            volume_mounts=[client.V1VolumeMount(mount_path='/data', name='io')],
            resources=client.V1ResourceRequirements(requests={
                # "cpu": 0.5
            }),
            command=["sh", "-c", self.input_script()],
        )

        # Define the main algorithm running container
        implementation = self.job.implementation
        main_container = client.V1Container(
            name="main",
            image=implementation.image,
            command=['sh'] if implementation.command else None,
            args=['-c', implementation.command] if implementation.command else None,
            resources=client.V1ResourceRequirements(
                requests = {
                    "nvidia.com/gpu": "1"
                },
                limits = {
                    "nvidia.com/gpu": "1"
                }
            ),
            volume_mounts=[client.V1VolumeMount(mount_path='/data', name='io')],
        )

        output_container = client.V1Container(
            name=f"output",
            image='python:2-alpine',
            volume_mounts=[client.V1VolumeMount(mount_path='/data', name='io')],
            resources=client.V1ResourceRequirements(requests={
                # "cpu": 0.5
            }),
            command=["sh", "-c", self.output_script()],
        )

        # Define the pod running the job. As there are no exit containers possible,
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(name=self.job_name()),
            spec=client.V1PodSpec(
                automount_service_account_token=False,
                restart_policy="Never",
                init_containers=[input_container, main_container],
                containers=[output_container],
                volumes=[client.V1Volume(
                    name='io',
                    persistent_volume_claim={'claimName': self.io_pvc_name()}
                )],
                tolerations=[client.V1Toleration(
                    key='nvidia.com/gpu',
                    operator='Exists',
                    effect='NoSchedule'
                )],
            )
        )

        job = client.V1Job(
            metadata=client.V1ObjectMeta(name=self.job_name()),
            spec=client.V1JobSpec(template=template, backoff_limit=0),
        )

        client.BatchV1Api().create_namespaced_job(self.namespace, job)


    def __enter__(self):
        return self

    # cleanup when `with K8SJob` block goes out of scope
    def __exit__(self, exc_type, exc_val, exc_tb):
        for pod in self.get_pod_names():
            client.CoreV1Api().delete_namespaced_pod(
                name=pod,
                namespace=self.namespace,
                body={}
            )

        client.BatchV1Api().delete_namespaced_job(
            name=self.job_name(),
            namespace=self.namespace,
            body={}
        )

        client.CoreV1Api().delete_namespaced_persistent_volume_claim(
            name=self.io_pvc_name(),
            namespace=self.namespace,
            body={}
        )

    # has the job failed?
    @property
    def failed(self):
        return self.status().failed

    # has the job succeeded?
    @property
    def succeeded(self):
        return self.status().succeeded

    # get status dict.
    def status(self):
        """Get the status of the job
        """
        r = client.BatchV1Api().read_namespaced_job_status(
            name=self.job_name(),
            namespace=self.namespace,
        )
        return r.status

    # get pod names for this Job (should be a single pod, unless we enable retries (e.g. using backoffLimit)
    def get_pod_names(self):
        podlist = client.CoreV1Api().list_namespaced_pod(
            namespace=self.namespace,
            label_selector=f"job-name={self.job_name()}"
        )

        return [pod.metadata.name for pod in podlist.items]

    # get logs dict as { pod_name: { container_name: log } }
    def get_logs(self, container=None, previous=False):
        if container is None:
            containers = ["input", "main", "output"]
        else:
            containers = [container]

        logs = {}
        for podname in self.get_pod_names():
            for container in containers:
                try:
                    r = client.CoreV1Api().read_namespaced_pod_log(
                        name=podname,
                        namespace=self.namespace,
                        container=container,
                        follow=False,
                        pretty=True,
                        previous=previous,
                        timestamps=True
                    )
                except ApiException as m:
                    # print(m)
                    continue

                if podname not in logs:
                    logs[podname] = {}

                logs[podname][container] = r
        return logs

    def print_logs(self):
        print(self.get_text_logs())

    # flatten logs dict into text structure
    def get_text_logs(self):
        logs = self.get_logs()
        text_log = ""
        for podname, logs in logs.items():
            text_log += "\n"
            text_log += f"Pod: {podname}\n"
            for container, log in logs.items():
                text_log += "\n"
                text_log += f"Container: {container}\n"
                text_log += log
        return text_log