from kubernetes.config import load_incluster_config, load_kube_config
from kubernetes import client
from kubernetes.client.rest import ApiException
import time
import json


class K8sJob(object):
    def __init__(self, job_id, namespace, image, s3_bucket, inputs, outputs, volume_defs=None, blocking=False, delete_old=True):
        """
        Run a Kubernetes job based on a simple algorithm container.

        The job runs three containers:
        - init: downloads the input files from the object storage into the input volume.
        - main: runs the algorithm container
        - exit: uploads the output files from the output volume to the object storage, as a single zip file.

        The algorithm container should have its own command or entrypoint defined (i.e., it should run independently), and
        it should read input data from /input/ and write all output files to /output/. These folder will be provided as
        mounts by the Kubernetes cluster.

        S3 access credentials should be stored in a secret.

        Args:
            job_id (str): the ID used as the K8s job name
            namespace (str): the namespace where the job is to be run
            image (str): the docker image that contains the code to run
            s3_bucket (str): the bucket containing the input and output data
            inputs (dict): a dict of (object storage key, filename) pairs for the input files
            outputs (dict): a dict of (object storage key, filename) pairs that is used for storing the algorithm output
            volume_defs (dict): a dict containing (volume name, mount point) items: all these are mounted in all containers that are part of the job
            blocking (bool): whether to wait for the job to finish
        """

        self.job_id = str(job_id)
        self.namespace = namespace
        self.image = image
        if volume_defs is None:
            self.volume_defs = {"input-volume": "/input", "output-volume": "/output"}
        else:
            self.volume_defs = volume_defs
        self.inputs = inputs
        self.outputs = outputs
        self.s3_bucket = s3_bucket
        self.s3_credentials_secret = "do-spaces"
        self.data_io_image = "docker-registry.roel.dev.eyrabenchmark.net/eyra-data-io"

        self.volumes = []
        self.volume_mounts = []
        self.pods = []
        self.blocking = blocking

        incluster = False
        if incluster:
            load_incluster_config()
        else:
            load_kube_config()

        if delete_old:
            pass
            # batch_v1 = client.BatchV1Api()
            # batch_v1.list_namespaced_job(self.namespace, )
            # delete_options = client.V1DeleteOptions()
            # batch_v1.delete_namespaced_job(self.job_id, self.namespace, delete_options)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up all resources, if required
        pass

    def _create_io_volumes(self):
        """Creates the Kubernetes volumes for input and output data. These are normal volumes, whose life cycle is tied
        to the pod they live in.
        """

        self.volumes = []
        self.volume_mounts = []

        for volume_name, mount_point in self.volume_defs.items():
            self.volumes.append(
                client.V1Volume(name=volume_name)
            )
            self.volume_mounts.append(
                client.V1VolumeMount(mount_path=mount_point, name=volume_name)
            )

    def _run_pod(self):
        """Defines a Kubernetes job using the python API and runs it.
        """

        batch_v1 = client.BatchV1Api()
        meta = client.V1ObjectMeta(name=self.job_id)

        # Set up all environment variables for s3 object storage access
        env_vars = [
            client.V1EnvVar(
                name="S3_ENDPOINT",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name=self.s3_credentials_secret,
                        key="endpoint"
                    )
                )
            ),
            client.V1EnvVar(
                name="S3_ACCESS_KEY",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name=self.s3_credentials_secret,
                        key="key"
                    )
                )
            ),
            client.V1EnvVar(
                name="S3_SECRET_KEY",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name=self.s3_credentials_secret,
                        key="secret"
                    )
                )
            ),
            client.V1EnvVar(
                name="S3_REGION",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name=self.s3_credentials_secret,
                        key="region"
                    )
                )
            ),
            client.V1EnvVar(
                name="S3_BUCKET",
                value=self.s3_bucket
            ),
            client.V1EnvVar(
                name="S3_OBJECT_KEYS_INPUT",
                value=json.dumps(self.inputs)
            ),
            client.V1EnvVar(
                name="S3_OBJECT_KEY_OUTPUT",
                value=json.dumps(self.outputs)
            )
        ]

        # Define the input container that performs input data provisioning
        input_container = client.V1Container(
            name=self.job_id + "-input",
            image=self.data_io_image,
            volume_mounts=self.volume_mounts,
            env=env_vars,
            resources=client.V1ResourceRequirements(requests={"cpu": 0.5}),
            command=[
                "bash",
                "-c",
                "python /tmp/data_io.py load",
            ],
        )

        # Define the main algorithm running container
        container = client.V1Container(
            name=self.job_id + "-main",
            image=self.image,
            resources=client.V1ResourceRequirements(requests={"cpu": 1.0}),
            volume_mounts=self.volume_mounts,
        )

        # Define the output container that uploads all results to the object storage
        output_container = client.V1Container(
            name=self.job_id + "-output",
            image=self.data_io_image,
            volume_mounts=self.volume_mounts,
            env=env_vars,
            resources=client.V1ResourceRequirements(requests={"cpu": 0.5}),
            command=[
                "bash",
                "-c",
                "python /tmp/data_io.py store",
            ],
        )

        # Define the pod running the job. As there are no exit containers possible,
        podspec = client.V1PodSpec(
            restart_policy="Never",
            init_containers=[input_container, container],
            containers=[output_container],
            volumes=self.volumes,
        )

        template = client.V1PodTemplateSpec(metadata=meta, spec=podspec)

        # Define the job
        jobspec = client.V1JobSpec(template=template, backoff_limit=1)
        job = client.V1Job(metadata=meta, spec=jobspec)

        # Schedule the job on the cluster
        r = batch_v1.create_namespaced_job(self.namespace, job)

        if self.blocking:
            print("Executing job...")
            while True:
                s = self.status()
                print(s)

                logs = self.get_logs()
                for podname, logs in logs.items():
                    print()
                    print(podname)
                    for container, log in logs.items():
                        print()
                        print(container)
                        print(log)

                if not s.active:
                    if s.failed or s.succeeded:
                        break
                time.sleep(1)

            if s.failed:
                print("Job failed!")
            if s.succeeded:
                print("Job succeeded!")

        return

    @property
    def failed(self):
        return self.status().failed

    @property
    def succeeded(self):
        return self.status().succeeded

    def execute(self):
        """The main entrypoint for running the job.
        """
        self._create_io_volumes()
        self._run_pod()

    def status(self):
        """Get the status of the job
        """
        batch_v1 = client.BatchV1Api()
        r = batch_v1.read_namespaced_job_status(
            self.job_id, self.namespace
        )
        return r.status

    def get_logs(self, container=None, previous=False):
        core_v1 = client.CoreV1Api()

        if container is None:
            containers = [self.job_id + "-input", self.job_id + "-main", self.job_id + "-output"]
        else:
            containers = [container]

        podlist = core_v1.list_namespaced_pod(namespace=self.namespace, label_selector=f"job-name={self.job_id}")
        podnames = [p.metadata.name for p in podlist.items]


        logs = {}
        for podname in podnames:
            for container in containers:
                try:
                    r = core_v1.read_namespaced_pod_log(
                        name=podname,
                        namespace=self.namespace,
                        container=container,
                        follow=False,
                        pretty=True,
                        previous=previous,
                        timestamps=True
                    )
                except ApiException as m:
                    print(m)
                    continue

                if podname not in logs:
                    logs[podname] = {}

                logs[podname][container] = r
        return logs


if __name__ == "__main__":
    algorithm_id = "algorithm_a_0148a9ce-34f6-11e9-b346-00155d544bd9"
    #algorithm_id = "algorithm_b_c0d8fb92-35ad-11e9-91d4-00155d544bd9"
    #algorithm_id = "algorithm_c_eea72dc0-34fc-11e9-aa23-00155d544bd9"

    evaluation_id = "evaluation_a_9d942b7a-35bc-11e9-a52a-00155d544bd9"
    #input_zip_id = "result_algorithm_a_0148a9ce-34f6-11e9-b346-00155d544bd9.zip"
    input_zip_id = "result_algorithm_b_c0d8fb92-35ad-11e9-91d4-00155d544bd9.zip"
    #input_zip_id = "result_algorithm_c_eea72dc0-34fc-11e9-aa23-00155d544bd9.zip"

    kj = K8sJob(
        job_id=f"{algorithm_id.replace('_', '-')}",
        namespace="dev-maarten",
        image=f"docker-registry.roel.dev.eyrabenchmark.net/{algorithm_id}",
        s3_bucket="eyra-datasets",
        input_object_keys=["test_data/X_test.npy"],
        output_object_key=f"test_data/result_{algorithm_id}.zip",
        blocking=True

        # Evaluation container stuff
        # input_object_keys=[f"test_data/{input_zip_id}", "test_data/gt_test.npy"],
        # output_object_key=f"test_data/evaluation_{input_zip_id}"    )
    )

    kj.execute()

