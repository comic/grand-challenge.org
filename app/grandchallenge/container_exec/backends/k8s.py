from kubernetes.config import load_incluster_config, load_kube_config
from kubernetes import client
from kubernetes.stream import stream
import tarfile
from tempfile import TemporaryFile
from pathlib import Path
import time


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

        while True:
            r = batch_v1.read_namespaced_job_status(
                self.job_id, self.namespace
            )
            if not r.status.active:
                break
            time.sleep(1)

        if r.status.failed:
            print("Main job failed!")
        if r.status.succeeded:
            print("Main job succeeded!")

        return

    def get_result(self):
        filename = ""
        pod_name = self.job_id + "-iopod"

        core_v1 = client.CoreV1Api()
        meta = client.V1ObjectMeta(name=pod_name)
        container = client.V1Container(
            name=self.job_id,
            image="alpine:3.8",
            volume_mounts=self.volume_mounts,
        )
        podspec = client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=self.volumes,
        )
        pod = client.V1Pod(metadata=meta, spec=podspec)

        r = core_v1.create_namespaced_pod(self.namespace, pod)

        while True:
            r = core_v1.read_namespaced_pod_status(pod_name, self.namespace)
            if r.status == "Running":
                break
            time.sleep(1)

        result = get_file(filename, pod_name, self.namespace)

        r = core_v1.delete_namespaced_pod(pod_name, self.namespace, pod)
        return result

    def provision_input_volume(self):
        filename = ""
        pod_name = self.job_id + "-iopod"

        core_v1 = client.CoreV1Api()
        meta = client.V1ObjectMeta(name=pod_name)
        container = client.V1Container(
            name=self.job_id,
            image="alpine:3.8",
            volume_mounts=self.volume_mounts,
        )
        podspec = client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=self.volumes,
        )
        pod = client.V1Pod(metadata=meta, spec=podspec)

        r = core_v1.create_namespaced_pod(self.namespace, pod)

        while True:
            r = core_v1.read_namespaced_pod_status(pod_name, self.namespace)
            if r.status == "Running":
                break
            time.sleep(1)

        put_file(filename, pod_name, self.namespace)

        r = core_v1.delete_namespaced_pod(pod_name, self.namespace, pod)

    def execute(self):
        self.create_io_volumes()
        self.provision_input_volume()
        self.execute_job()
        return self.get_result()


class K8sExecutor(object):
    def __init__(self, job_id, k8s_namespace):
        self.job_id = str(job_id)
        self.k8s_namespace = k8s_namespace
        self.input_volume = f"{self.job_id}-input"
        self.output_volume = f"{self.job_id}-output"

        incluster = False

        if incluster:
            load_incluster_config()
        else:
            load_kube_config()

    def execute(self):
        self.create_io_volumes()
        batch_v1 = client.BatchV1Api()
        meta = client.V1ObjectMeta(name="test-job")
        input_claim = client.V1PersistentVolumeClaimVolumeSource(
            claim_name=self.input_volume
        )
        input_volume = client.V1Volume(
            name="eyra-dev-roel-input-volume",
            persistent_volume_claim=input_claim,
        )
        output_claim = client.V1PersistentVolumeClaimVolumeSource(
            claim_name=self.output_volume
        )
        output_volume = client.V1Volume(
            name="eyra-dev-roel-output-volume",
            persistent_volume_claim=output_claim,
        )
        volumes = [input_volume, output_volume]
        input_volume_mount = client.V1VolumeMount(
            mount_path="/input/", name="eyra-dev-roel-input-volume"
        )
        output_volume_mount = client.V1VolumeMount(
            mount_path="/output/", name="eyra-dev-roel-output-volume"
        )
        volume_mounts = [input_volume_mount, output_volume_mount]
        container = client.V1Container(
            name="test",
            image="docker-registry.roel.dev.eyrabenchmark.net/rzi/blabla",
            volume_mounts=volume_mounts,
        )
        podspec = client.V1PodSpec(
            restart_policy="Never", containers=[container], volumes=volumes
        )
        template = client.V1PodTemplateSpec(metadata=meta, spec=podspec)
        jobspec = client.V1JobSpec(template=template, backoff_limit=3)
        job = client.V1Job(metadata=meta, spec=jobspec)

        r = batch_v1.create_namespaced_job(self.k8s_namespace, job)

    def create_io_volumes(self):
        core_v1 = client.CoreV1Api()
        for volume in [self.input_volume, self.output_volume]:
            meta = client.V1ObjectMeta(name=volume)
            resources = client.V1ResourceRequirements(
                requests={"storage": "8Gi"}
            )
            spec = client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"], resources=resources
            )
            pvc = client.V1PersistentVolumeClaim(metadata=meta, spec=spec)
            core_v1.create_namespaced_persistent_volume_claim(
                self.k8s_namespace, pvc
            )

    def provision_input_volume(self):
        pass

    def copy_input_files(self):
        pass

    def get_result(self):
        pass


def put_file(source_file, pod_name, namespace):
    core_v1 = client.CoreV1Api()

    exec_command = ["tar", "xvf", "-", "-C", "/app"]
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
            tar.add(source_file)

        tar_buffer.seek(0)
        commands = []
        commands.append(tar_buffer.read().decode())
        print(commands)

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

    exec_command = ["tar", "cf", "-", src.name, "-C", str(src.parents[0])]

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
            f = tar.extractfile(src.name)
            content = f.read().decode()
    return content


if __name__ == "__main__":
    incluster = False

    if incluster:
        load_incluster_config()
    else:
        load_kube_config()

    put_file("bliep.txt", "eyra-dev-roel-web-6b96dfb97-78csk", "dev-roel")
