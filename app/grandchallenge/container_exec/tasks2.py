if __name__ == "__main__":
    from django import setup
    setup()

from grandchallenge.eyra_benchmarks.models import Benchmark, Submission


if __name__ == "__main__":
    submission = Submission.objects.get(pk=)
    benchmark = Benchmark.objects
    f = Benchmark.objects.all()[0].test_datafile.file

    print(f.name)
    print(f.url)
