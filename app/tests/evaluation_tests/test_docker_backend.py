from grandchallenge.components.backends.docker import DockerExecutor
from grandchallenge.components.models import GPUTypeChoices


def test_internal_logs_filtered():
    logs = '2022-05-31T09:47:57.371317000Z {"log": "Found credentials in environment variables.", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n2022-05-31T09:47:57.478222400Z {"log": "Downloading self.bucket_key=\'/evaluation/evaluation/9b966b3f-3fa2-42f2-a9ae-8457565f9644/predictions.zip\' from self.bucket_name=\'grand-challenge-components-inputs\' to dest_file=PosixPath(\'/input/predictions.zip\')", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n2022-05-31T09:47:57.503693300Z {"log": "Extracting member[\'src\']=\'submission/submission.csv\' from /tmp/tmpfsxjvtow/src.zip to /input/submission.csv", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n2022-05-31T09:47:57.504206200Z {"log": "Extracting member[\'src\']=\'submission/images/image10x10x10.mhd\' from /tmp/tmpfsxjvtow/src.zip to /input/images/image10x10x10.mhd", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n2022-05-31T09:47:57.504533600Z {"log": "Extracting member[\'src\']=\'submission/images/image10x10x10.zraw\' from /tmp/tmpfsxjvtow/src.zip to /input/images/image10x10x10.zraw", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n2022-05-31T09:48:03.205773000Z {"log": "Greetings from stdout", "level": "INFO", "source": "stdout", "internal": false, "task": "evaluation-evaluation-9b966b3f-3fa2-42f2-a9ae-8457565f9644"}\n2022-05-31T09:48:03.218474800Z {"log": "Uploading src_file=\'/output/metrics.json\' to self.bucket_name=\'grand-challenge-components-outputs\' with self.bucket_key=\'evaluation/evaluation/9b966b3f-3fa2-42f2-a9ae-8457565f9644/metrics.json\'", "level": "INFO", "source": "stdout", "internal": true, "task": null}\n'

    executor = DockerExecutor(
        job_id="test",
        exec_image_repo_tag="test",
        memory_limit=4,
        time_limit=100,
        requires_gpu=False,
        desired_gpu_type=GPUTypeChoices.T4,
    )
    executor._parse_loglines(loglines=logs.splitlines())

    assert (
        executor.stdout
        == "2022-05-31T09:48:03.205773000Z Greetings from stdout"
    )
