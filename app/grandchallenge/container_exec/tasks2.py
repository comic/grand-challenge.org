if __name__ == "__main__":
    from django import setup
    setup()

from grandchallenge.eyra_benchmarks.models import Benchmark, Submission
from grandchallenge.container_exec.backends.k8s import K8sJob


if __name__ == "__main__":
    submission = Submission.objects.all()[0]

    benchmark = submission.benchmark
    algorithm = submission.algorithm
    f = benchmark.test_datafile.file

    job_id = f"submission-{submission.pk}"
    namespace = f"benchmark-{benchmark.pk}"
    image = algorithm.container
    s3_bucket = ""
    input_object_keys = [benchmark.test_datafile, benchmark.ground_truth_datafile]
    output_object_key = ""

    job = K8sJob(
        job_id=job_id,
        namespace=namespace,
        image=image,
        s3_bucket=s3_bucket,
        input_object_keys=input_object_keys,
        output_object_key=output_object_key
    )