from kubernetes.config import load_incluster_config, load_kube_config
from kubernetes import client
from kubernetes.stream import stream
from kubernetes.client.rest import ApiException
import tarfile
from tempfile import TemporaryFile
from pathlib import Path
import time


"""
New idea:
Create a pod with two containers. One is the data provisioner: it loads the required
input data from the object storage (Digital Ocean Spaces).
"""

REGION = "ams3"
ACCESS_KEY = "V5OTPTWOTJX4LSA3DBNP"
SECRET_KEY = "wyewQ5K30HvnBii/t7bqfI5ovAjKJruHFXfLGVUgeOI"
BUCKET = "eyra-datasets"


class K8sJob(object):
    def __init__(self, job_id, namespace, image, volume_defs, input_object_keys, output_object_key):
        self.job_id = str(job_id)
        self.namespace = namespace
        self.image = image
        self.volume_defs = volume_defs
        self.input_object_keys = input_object_keys
        self.output_object_key = output_object_key

        self.volumes = []
        self.volume_mounts = []
        self.pods = []

        incluster = False

        if incluster:
            load_incluster_config()
        else:
            load_kube_config()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up all resources
        for pod in self.pods:
            pass

    def create_io_volumes(self):
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
        batch_v1 = client.BatchV1Api()
        meta = client.V1ObjectMeta(name=self.job_id)

        env_vars = [
            client.V1EnvVar(
                name="S3_ENDPOINT",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name="do-spaces",
                        key="endpoint"
                    )
                )
            ),
            client.V1EnvVar(
                name="S3_ACCESS_KEY",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name="do-spaces",
                        key="key"
                    )
                )
            ),
            client.V1EnvVar(
                name="S3_SECRET_KEY",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name="do-spaces",
                        key="secret"
                    )
                )
            ),
            client.V1EnvVar(
                name="S3_REGION",
                value="ams3"
            ),
            client.V1EnvVar(
                name="S3_BUCKET",
                value="eyra-datasets"
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

        init_container = client.V1Container(
            name=self.job_id + "-init",
            image="docker-registry.roel.dev.eyrabenchmark.net/eyra-data-io",
            volume_mounts=self.volume_mounts,
            env=env_vars,
            resources=client.V1ResourceRequirements(requests={"cpu": 0.5}),
            command=[
                "bash",
                "-c",
                "python /tmp/data_io.py load",
            ],
        )

        container = client.V1Container(
            name=self.job_id,
            image=self.image,
            resources=client.V1ResourceRequirements(requests={"cpu": 1.0}),
            volume_mounts=self.volume_mounts,
        )

        exit_container = client.V1Container(
            name=self.job_id + "-exit",
            image="docker-registry.roel.dev.eyrabenchmark.net/eyra-data-io",
            volume_mounts=self.volume_mounts,
            env=env_vars,
            resources=client.V1ResourceRequirements(requests={"cpu": 0.5}),
            command=[
                "bash",
                "-c",
                "python /tmp/data_io.py store",
            ],
        )
        podspec = client.V1PodSpec(
            restart_policy="Never",
            init_containers=[init_container, container],
            containers=[exit_container],
            volumes=self.volumes,
        )

        template = client.V1PodTemplateSpec(metadata=meta, spec=podspec)
        jobspec = client.V1JobSpec(template=template, backoff_limit=1)
        job = client.V1Job(metadata=meta, spec=jobspec)

        r = batch_v1.create_namespaced_job(self.namespace, job)

        print("Executing job...")
        while True:
            r = batch_v1.read_namespaced_job_status(
                self.job_id, self.namespace
            )
            print(r.status)
            if not r.status.active:
                if r.status.failed or r.status.succeeded:
                    break
            time.sleep(1)

        if r.status.failed:
            print("Job failed!")
        if r.status.succeeded:
            print("Job succeeded!")

        return

    def execute(self):
        self.create_io_volumes()
        self.run_pod()


if __name__ == "__main__":
    algorithm_id = "algorithm_a_0148a9ce-34f6-11e9-b346-00155d544bd9"
    #algorithm_id = "algorithm_b_c0d8fb92-35ad-11e9-91d4-00155d544bd9"
    #algorithm_id = "algorithm_c_eea72dc0-34fc-11e9-aa23-00155d544bd9"

    kj = K8sJob(
        f"test-rzi-{algorithm_id.replace('_', '-')}",
        "dev-roel",
        f"docker-registry.roel.dev.eyrabenchmark.net/{algorithm_id}",
        {"input-volume": "/input", "output-volume": "/output"},
        ["test_data/X_test.npy"],
        f"test_data/result_{algorithm_id}.zip"
    )
    kj.execute()
