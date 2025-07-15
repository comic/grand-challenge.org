import grp
import json
import os
import pwd
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from shutil import copy
from tempfile import TemporaryDirectory
from warnings import warn

# noinspection PyUnresolvedReferences
import psutil

# noinspection PyUnresolvedReferences
import pynvml


def check_connectivity():
    ssl_context = ssl.create_default_context()

    try:
        urllib.request.urlopen(
            "https://google.com/", timeout=5, context=ssl_context
        )
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


def check_memory():
    memory = psutil.virtual_memory()
    print(f"MEMORY - Total: {memory.total / (1024 * 1024 * 1024):.2f} GB")
    print(
        f"MEMORY - Available: {memory.available / (1024 * 1024 * 1024):.2f} GB"
    )
    print(f"MEMORY - Used: {memory.used / (1024 * 1024 * 1024):.2f} GB")
    print(f"MEMORY - Free: {memory.free / (1024 * 1024 * 1024):.2f} GB")


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


def check_temporary_file():
    with TemporaryDirectory() as tmp_dir:
        file = Path(tmp_dir) / "test"
        file.touch()
        print(file)

        directory = Path(tmp_dir) / "1" / "2"
        directory.mkdir(parents=True)
        print(directory)

    file = Path("/tmp") / "test"
    file.touch()
    print(file)

    tmp_directory = Path("/tmp") / "1" / "2"
    tmp_directory.mkdir(parents=True)
    print(directory)

    print("TEMPORARY FILE - successfully created")


def check_permissions():
    try:
        Path("/tmp").chmod(0o777)
        warn("COULD CHANGE DIRECTORY PERMS!")
    except PermissionError as e:
        print(f"CHMOD PERMISSIONS - Could not change permissions {e}")


def create_output():
    res = {"score": 1}  # dummy metric for ranking on leaderboard
    files = {x for x in Path("/input").rglob("*") if x.is_file()}

    for file in files:
        try:
            with open(file) as f:
                val = json.load(f)
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


def generate_cpu_load(*, duration):
    start_time = time.time()
    while time.time() - start_time < duration:
        pass


if __name__ == "__main__":
    print(f"Current user: {pwd.getpwuid(os.getuid())}")
    print(f"Current group: {grp.getgrgid(os.getgid())}")
    print(
        f"Current groups: {[(gid, grp.getgrgid(gid).gr_name) for gid in os.getgroups()]}"
    )
    print("")

    for k, v in os.environ.items():
        print(f"{k}={v}")
    print("")

    check_connectivity()
    print("")

    check_partitions()
    print("")

    check_memory()
    print("")

    check_cuda()
    print("")

    check_temporary_file()
    print("")

    check_permissions()
    print("")

    print("Generating CPU Load")
    generate_cpu_load(duration=0.001)
    print("CPU Load Complete")

    create_output()
