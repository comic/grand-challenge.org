from kubernetes import config
from kubernetes import client


class K8sExecutor(object):
    def __init__(self):
        incluster = False

        if incluster:
            config.load_incluster_config()
        else:
            config.load_kube_config()

    def execute(self):
        batch_v1 = client.BatchV1Api()
        meta = client.V1ObjectMeta(name="test-job")
        input_claim = client.V1PersistentVolumeClaimVolumeSource(
            claim_name="eyra-dev-roel-input"
        )
        input_volume = client.V1Volume(
            name="eyra-dev-roel-input-volume",
            persistent_volume_claim=input_claim,
        )
        output_claim = client.V1PersistentVolumeClaimVolumeSource(
            claim_name="eyra-dev-roel-output"
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

        r = batch_v1.create_namespaced_job("dev-roel", job)


if __name__ == "__main__":
    ke = K8sExecutor()
    ke.execute()
