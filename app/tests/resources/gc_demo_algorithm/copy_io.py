import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from shutil import copy
from warnings import warn

# noinspection PyUnresolvedReferences
import psutil

# noinspection PyUnresolvedReferences
import pynvml


def check_connectivity():
    try:
        urllib.request.urlopen("https://google.com/", timeout=5)
        warn("COULD GOOGLE!")
    except urllib.error.URLError as e:
        print(f"CONNECTIVITY - Could not google: {e.reason}")


def check_partitions():
    disk_partitions = psutil.disk_partitions(all=True)

    print(
        f"{'Filesystem':<32}"
        f"{'Mountpoint':<64}"
        f"Total / GB\t"
        f"Free / GB\t"
        f"Owner\t"
        f"Permissions"
    )

    for partition in disk_partitions:
        partition_info = psutil.disk_usage(partition.mountpoint)
        partition_stat = os.stat(Path(partition.mountpoint))
        print(
            f"{partition.device:<32}"
            f"{partition.mountpoint:<64}"
            f"{partition_info.total / (1024 * 1024 * 1024):.2f}\t\t"
            f"{partition_info.free / (1024 * 1024 * 1024):.2f}\t"
            f"{partition_stat.st_uid}:{partition_stat.st_gid}\t\t"
            f"{oct(partition_stat.st_mode)}"
        )


def check_cuda():
    try:
        pynvml.nvmlInit()
        pynvml.nvmlDeviceGetCount()

        print(f"CUDA - Driver Version: {pynvml.nvmlSystemGetDriverVersion()}")
        print(
            f"CUDA - CUDA Driver Version: {pynvml.nvmlSystemGetCudaDriverVersion()}"
        )

        device_count = pynvml.nvmlDeviceGetCount()
        for ii in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(ii)
            print(f"CUDA - Device {ii}: {pynvml.nvmlDeviceGetName(handle)}")

        pynvml.nvmlShutdown()
    except pynvml.NVMLError as error:
        print(f"CUDA - Pynvml error: {error}")


def create_output():
    res = {"score": 1}  # dummy metric for ranking on leaderboard
    files = {x for x in Path("/input").rglob("*") if x.is_file()}

    for file in files:
        try:
            with open(file) as f:
                val = json.loads(f.read())
        except Exception as e:
            warn(f"Could not load {file} as json, {e}")
            val = "file"

        res[str(file.absolute())] = val

        # Copy all the input files to output
        new_file = Path("/output/") / file.relative_to("/input/")
        new_file.parent.mkdir(parents=True, exist_ok=True)
        copy(file, new_file)

    for output_filename in ["results", "metrics"]:
        with open(f"/output/{output_filename}.json", "w") as f:
            f.write(json.dumps(res))


if __name__ == "__main__":
    check_connectivity()
    print("")

    check_partitions()
    print("")

    check_cuda()
    print("")

    create_output()
