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
input data from the object storage (Digital Ocean Spaces)
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

        for pvc in self.pvcs:
            pass

    def create_io_volumes(self):
        core_v1 = client.CoreV1Api()

        self.pvcs = []
        self.pvcss = []
        self.volumes = []
        self.volume_mounts = []

        for volume_name, mount_point in self.volume_defs.items():
            self.pvcss.append(
                client.V1PersistentVolumeClaimVolumeSource(
                    claim_name=volume_name
                )
            )
            self.volumes.append(
                client.V1Volume(
                    name=volume_name, persistent_volume_claim=self.pvcss[-1]
                )
            )
            self.volume_mounts.append(
                client.V1VolumeMount(mount_path=mount_point, name=volume_name)
            )

            meta = client.V1ObjectMeta(name=volume_name)
            resources = client.V1ResourceRequirements(
                requests={"storage": "8Gi"}
            )
            spec = client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"], resources=resources
            )
            self.pvcs.append(
                client.V1PersistentVolumeClaim(metadata=meta, spec=spec)
            )
            core_v1.create_namespaced_persistent_volume_claim(
                self.namespace, self.pvcs[-1]
            )

            print("Checking PVC status...")
            while True:
                r = core_v1.read_namespaced_persistent_volume_claim_status(
                    volume_name, self.namespace
                )
                print(r.status.phase)
                if r.status.phase == "Bound":
                    break
                time.sleep(1)
            print("Done")

    def run_pod(self):
        batch_v1 = client.BatchV1Api()
        meta = client.V1ObjectMeta(name=self.job_id)

        init_container = client.V1Container(
            name=self.job_id + "-init",
            image="docker-registry.roel.dev.eyrabenchmark.net/eyra-dataloader",
            volume_mounts=self.volume_mounts,
            command=[
                "bash",
                "-c",
                "python /tmp/load_input.py ams3 V5OTPTWOTJX4LSA3DBNP wyewQ5K30HvnBii/t7bqfI5ovAjKJruHFXfLGVUgeOI eyra-datasets test_data/data.txt",
            ],
        )

        container = client.V1Container(
            name=self.job_id,
            image=self.image,
            volume_mounts=self.volume_mounts,
        )

        exit_container = client.V1Container(
            name=self.job_id + "-exit",
            image="docker-registry.roel.dev.eyrabenchmark.net/eyra-resultloader",
            volume_mounts=self.volume_mounts,
            command=[
                "bash",
                "-c",
                "python /tmp/store_result.py ams3 V5OTPTWOTJX4LSA3DBNP wyewQ5K30HvnBii/t7bqfI5ovAjKJruHFXfLGVUgeOI eyra-datasets test_data/result.txt",
            ],
        )
        podspec = client.V1PodSpec(
            restart_policy="Never",
            init_containers=[init_container, container],
            containers=[exit_container],
            volumes=self.volumes,
        )

        template = client.V1PodTemplateSpec(metadata=meta, spec=podspec)
        jobspec = client.V1JobSpec(template=template, backoff_limit=3)
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


class K8sJobOld(object):
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

        for pvc in self.pvcs:
            pass

    def create_io_volumes(self):
        core_v1 = client.CoreV1Api()

        self.pvcs = []
        self.pvcss = []
        self.volumes = []
        self.volume_mounts = []

        for volume_name, mount_point in self.volume_defs.items():
            self.pvcss.append(
                client.V1PersistentVolumeClaimVolumeSource(
                    claim_name=volume_name
                )
            )
            self.volumes.append(
                client.V1Volume(
                    name=volume_name, persistent_volume_claim=self.pvcss[-1]
                )
            )
            self.volume_mounts.append(
                client.V1VolumeMount(mount_path=mount_point, name=volume_name)
            )

            meta = client.V1ObjectMeta(name=volume_name)
            resources = client.V1ResourceRequirements(
                requests={"storage": "8Gi"}
            )
            spec = client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"], resources=resources
            )
            self.pvcs.append(
                client.V1PersistentVolumeClaim(metadata=meta, spec=spec)
            )
            core_v1.create_namespaced_persistent_volume_claim(
                self.namespace, self.pvcs[-1]
            )

            print("Checking PVC status...")
            while True:
                r = core_v1.read_namespaced_persistent_volume_claim_status(
                    volume_name, self.namespace
                )
                print(r.status.phase)
                if r.status.phase == "Bound":
                    break
                time.sleep(1)
            print("Done")

    def execute_job(self):
        batch_v1 = client.BatchV1Api()
        meta = client.V1ObjectMeta(name=self.job_id)

        container = client.V1Container(
            name=self.job_id,
            image=self.image,
            volume_mounts=self.volume_mounts,
        )
        podspec = client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=self.volumes,
        )
        template = client.V1PodTemplateSpec(metadata=meta, spec=podspec)
        jobspec = client.V1JobSpec(template=template, backoff_limit=3)
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

    def get_result(self):
        filename = Path("/output/data.txt")
        pod_name = self.job_id + "-output-pod"

        core_v1 = client.CoreV1Api()
        meta = client.V1ObjectMeta(name=pod_name)
        container = client.V1Container(
            name=self.job_id,
            image="alpine:3.8",
            command=["sleep", "300"],
            volume_mounts=self.volume_mounts,
        )
        podspec = client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=self.volumes,
        )
        pod = client.V1Pod(metadata=meta, spec=podspec)

        r = core_v1.create_namespaced_pod(self.namespace, pod)
        print("Waiting for output provisioning...")
        while True:
            r = core_v1.read_namespaced_pod_status(pod_name, self.namespace)
            print(r.status.phase)
            if r.status.phase == "Running":
                break
            time.sleep(1)

        result = get_file(filename, pod_name, self.namespace)
        print("Done")
        r = core_v1.delete_namespaced_pod(pod_name, self.namespace, pod)
        return result

    def provision_input_volume(self):
        source_filename = "data.txt"
        dest_filename = "/input/data.txt"
        pod_name = self.job_id + "-input-pod"

        core_v1 = client.CoreV1Api()
        meta = client.V1ObjectMeta(name=pod_name)
        container = client.V1Container(
            name=self.job_id,
            image="alpine:3.8",
            command=["sleep", "300"],
            volume_mounts=self.volume_mounts,
        )
        podspec = client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=self.volumes,
        )
        pod = client.V1Pod(metadata=meta, spec=podspec)

        r = core_v1.create_namespaced_pod(self.namespace, pod)
        print("Waiting for input provisioning...")
        while True:
            r = core_v1.read_namespaced_pod_status(pod_name, self.namespace)
            print(r.status.phase)
            if r.status.phase == "Running":
                break
            time.sleep(1)

        put_file(source_filename, dest_filename, pod_name, self.namespace)
        print("Done")
        r = core_v1.delete_namespaced_pod(pod_name, self.namespace, pod)
        print(r.status)
        print("Waiting for input provisioning teardown...")
        while True:
            try:
                r = core_v1.read_namespaced_pod_status(
                    pod_name, self.namespace
                )
            except ApiException:
                break
            print(r.status.phase)
            time.sleep(1)
        print("Done")

    def execute(self):
        self.create_io_volumes()
        self.provision_input_volume()
        self.execute_job()
        return self.get_result()


def put_file(source_file, dest_file, pod_name, namespace):
    core_v1 = client.CoreV1Api()

    exec_command = ["tar", "xvf", "-", "-C", "/"]
    resp = stream(
        core_v1.connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=exec_command,
        stderr=True,
        stdin=True,
        stdout=True,
        tty=False,
        _preload_content=False,
    )

    with TemporaryFile() as tar_buffer:
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            tar.add(source_file, arcname=dest_file)

        tar_buffer.seek(0)

        commands = []
        commands.append(tar_buffer.read().decode())

        while resp.is_open():
            resp.update(timeout=1)
            if resp.peek_stdout():
                print("STDOUT: {}".format(resp.read_stdout()))
            if resp.peek_stderr():
                print("STDERR: {}".format(resp.read_stderr()))
            if commands:
                c = commands.pop(0)
                resp.write_stdin(c)
            else:
                break
        resp.close()


def get_file(src: Path, pod_name: str, namespace: str):
    core_v1 = client.CoreV1Api()
    if not src.root:
        raise ValueError("You must supply an absolute path")

    exec_command = ["tar", "cf", "-", str(src), "-C", "/"]
    print(exec_command)

    with TemporaryFile() as tar_buffer:
        resp = stream(
            core_v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            command=exec_command,
            stderr=True,
            stdin=True,
            stdout=True,
            tty=False,
            _preload_content=False,
        )

        while resp.is_open():
            resp.update(timeout=1)
            if resp.peek_stdout():
                out = resp.read_stdout()
                tar_buffer.write(out.encode())
            if resp.peek_stderr():
                print("STDERR: {}".format(resp.read_stderr()))
        resp.close()

        tar_buffer.flush()
        tar_buffer.seek(0)

        with tarfile.open(mode="r", fileobj=tar_buffer) as tar:
            tar.list()
            f = tar.extractfile(str(src.relative_to("/")))
            content = f.read().decode()
    return content


if __name__ == "__main__":
    kj = K8sJob(
        "test-rzi-1",
        "dev-roel",
        "docker-registry.roel.dev.eyrabenchmark.net/rzi/blabla",
        {"test-rzi-input": "/input", "test-rzi-output": "/output"},
    )
    kj.execute()

    # put_file(
    #     "bliep.txt",
    #     "/tmp/bliep.txt",
    #     "eyra-dev-roel-web-6b96dfb97-78csk",
    #     "dev-roel",
    # )
    # get_file(
    #     Path("/tmp/bliep.txt"), "eyra-dev-roel-web-6b96dfb97-78csk", "dev-roel"
    # )
