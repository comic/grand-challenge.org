from kubernetes.config import load_incluster_config, load_kube_config
from kubernetes import client
import time


class K8sJob(object):
    def __init__(self, job_id, namespace, image, volume_defs, s3_bucket, input_object_keys, output_object_key, blocking=False):
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
            volume_defs (dict): a dict containing (volume name, mount point) items: all these are mounted in all containers that are part of the job
            s3_bucket (str): the bucket containing the input and output data
            input_object_keys (list): a list of the object storage keys for the input files
            output_object_key (str): the object storage key that is used for storing the algorithm output
            blocking (bool): whether to wait for the job to finish
        """

        self.job_id = str(job_id)
        self.namespace = namespace
        self.image = image
        self.volume_defs = volume_defs
        self.input_object_keys = input_object_keys
        self.output_object_key = output_object_key
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up all resources, if required
        pass

    def create_io_volumes(self):
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

    def run_pod(self):
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
                value=",".join(self.input_object_keys)
            ),
            client.V1EnvVar(
                name="S3_OBJECT_KEY_OUTPUT",
                value=self.output_object_key
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
                if not s.active:
                    if s.failed or s.succeeded:
                        break
                time.sleep(1)

            if s.failed:
                print("Job failed!")
            if s.succeeded:
                print("Job succeeded!")

        return

    def execute(self):
        """The main entrypoint for running the job.
        """
        self.create_io_volumes()
        self.run_pod()

    def status(self):
        """Get the status of the job
        """
        batch_v1 = client.BatchV1Api()
        r = batch_v1.read_namespaced_job_status(
            self.job_id, self.namespace
        )
        return r.status


if __name__ == "__main__":
    algorithm_id = "algorithm_a_0148a9ce-34f6-11e9-b346-00155d544bd9"
    #algorithm_id = "algorithm_b_c0d8fb92-35ad-11e9-91d4-00155d544bd9"
    #algorithm_id = "algorithm_c_eea72dc0-34fc-11e9-aa23-00155d544bd9"

    kj = K8sJob(
        job_id=f"{algorithm_id.replace('_', '-')}",
        namespace="dev-roel",
        image=f"docker-registry.roel.dev.eyrabenchmark.net/{algorithm_id}",
        volume_defs={"input-volume": "/input", "output-volume": "/output"},
        s3_bucket="eyra-datasets",
        input_object_keys=["test_data/X_test.npy"],
        output_object_key=f"test_data/result_{algorithm_id}.zip"
    )
    kj.execute()
