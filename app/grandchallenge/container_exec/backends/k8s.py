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
    def __init__(self, job_id, namespace, image, volume_defs):
        self.job_id = str(job_id)
        self.namespace = namespace
        self.image = image
        self.volume_defs = volume_defs
        self.pvcs = []
        self.pvcss = []
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

        # for pvc in self.pvcs:
        #     pass

    def create_io_volumes(self):
        # core_v1 = client.CoreV1Api()

        # self.pvcs = []
        # self.pvcss = []
        self.volumes = []
        self.volume_mounts = []

        for volume_name, mount_point in self.volume_defs.items():
            # self.pvcss.append(
            #     client.V1PersistentVolumeClaimVolumeSource(
            #         claim_name=volume_name
            #     )
            # )
            self.volumes.append(
                client.V1Volume(
                    name=volume_name,
                    # persistent_volume_claim=self.pvcss[-1]
                )
            )
            self.volume_mounts.append(
                client.V1VolumeMount(mount_path=mount_point, name=volume_name)
            )

            # meta = client.V1ObjectMeta(name=volume_name)
            # resources = client.V1ResourceRequirements(
            #     requests={"storage": "8Gi"}
            # )
            # spec = client.V1PersistentVolumeClaimSpec(
            #     access_modes=["ReadWriteOnce"], resources=resources
            # )
            # self.pvcs.append(
            #     client.V1PersistentVolumeClaim(metadata=meta, spec=spec)
            # )
            # core_v1.create_namespaced_persistent_volume_claim(
            #     self.namespace, self.pvcs[-1]
            # )

            # print("Checking PVC status...")
            # while True:
            #     r = core_v1.read_namespaced_persistent_volume_claim_status(
            #         volume_name, self.namespace
            #     )
            #     print(r.status.phase)
            #     if r.status.phase == "Bound":
            #         break
            #     time.sleep(1)
            # print("Done")

    def run_pod(self):
        batch_v1 = client.BatchV1Api()
        meta = client.V1ObjectMeta(name=self.job_id)

        env_vars = [
            client.V1EnvVar(
                name="S3_ACCESS_KEY",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name="eyra-spaces-credentials",
                        key="s3AccessKey"
                    )
                )
            ),
            client.V1EnvVar(
                name="S3_SECRET_KEY",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name="eyra-spaces-credentials",
                        key="s3SecretKey"
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
                name="S3_OBJECT_KEY_INPUT",
                value="test_data/data.zip"
            ),
            client.V1EnvVar(
                name="S3_OBJECT_KEY_OUTPUT",
                value="test_data/result.zip"
            )
        ]

        init_container = client.V1Container(
            name=self.job_id + "-init",
            image="docker-registry.roel.dev.eyrabenchmark.net/eyra-data-io",
            volume_mounts=self.volume_mounts,
            env=env_vars,
            command=[
                "bash",
                "-c",
                "python /tmp/data_io.py load",
            ],
        )

        container = client.V1Container(
            name=self.job_id,
            image=self.image,
            volume_mounts=self.volume_mounts,
        )

        exit_container = client.V1Container(
            name=self.job_id + "-exit",
            image="docker-registry.roel.dev.eyrabenchmark.net/eyra-data-io",
            volume_mounts=self.volume_mounts,
            env=env_vars,
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
    kj = K8sJob(
        "test-rzi-1",
        "dev-roel",
        "docker-registry.roel.dev.eyrabenchmark.net/simpletest",
        {"input-volume": "/input", "output-volume": "/output"},
    )
    kj.execute()
