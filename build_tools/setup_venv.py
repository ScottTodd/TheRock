#!/usr/bin/env python

"""Sets up a Python venv and optionally installs rocm packages into it.

* https://docs.python.org/3/library/venv.html
* https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#create-and-use-virtual-environments

There are a few modes this can be used in:

* Minimally, this is equivalent to `python -m venv .venv`:

    ```
    python setup_venv.py .venv
    ```
"""

import argparse
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys

THIS_DIR = Path(__file__).resolve().parent

is_windows = platform.system() == "Windows"


def exec(args: list[str | Path], cwd: Path = Path.cwd()):
    args = [str(arg) for arg in args]
    print(f"++ Exec [{cwd}]$ {shlex.join(args)}")
    subprocess.check_call(args, cwd=str(cwd), stdin=subprocess.DEVNULL)


def find_venv_python(venv_path: Path) -> Path | None:
    paths = [venv_path / "bin" / "python", venv_path / "Scripts" / "python.exe"]
    for p in paths:
        if p.exists():
            return p
    return None


def create_venv(venv_dir: Path):
    cwd = Path.cwd()

    print(f"Creating venv at '{venv_dir}'")

    # Log some other variations of the path too.
    try:
        venv_dir_relative = venv_dir.relative_to(cwd)
    except ValueError:
        venv_dir_relative = venv_dir
    venv_dir_resolved = venv_dir.resolve()
    print(f"  Relative dir: '{venv_dir_relative}'")
    print(f"  Resolved dir: '{venv_dir_resolved}'")
    print("")

    # Create with 'python -m venv' as needed.
    python_exe = find_venv_python(venv_dir)
    if python_exe:
        print(
            f"  Found existing python executable at '{python_exe}', skipping creation"
        )
        print("  Run again with --clean to clear the existing directory instead")
    else:
        exec([sys.executable, "-m", "venv", str(venv_dir)])


def upgrade_pip(python_exe: Path):
    print("")
    exec([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])


def run(args: argparse.Namespace):
    venv_dir = args.venv_dir

    if args.clean and venv_dir.exists():
        print(f"Clearing existing venv_dir '{venv_dir}'")
        shutil.rmtree(venv_dir)

    create_venv(venv_dir)
    python_exe = find_venv_python(venv_dir)

    upgrade_pip(python_exe)

    # Done with setup, log some useful information then exit.
    print("")
    print(f"Setup complete at '{venv_dir}'! Activate the venv with:")
    if is_windows:
        print(f"  {venv_dir}\\Scripts\\activate.bat")
    else:
        print(f"  source {venv_dir}/bin/activate")


def main(argv: list[str]):
    p = argparse.ArgumentParser("setup_venv.py")
    p.add_argument(
        "venv_dir", type=Path, help="Directory in which to create the venv (e.g. .venv)"
    )
    p.add_argument(
        "--clean",
        action=argparse.BooleanOptionalAction,
        help="If the venv directory already exists, clear it and start fresh",
    )
    p.add_argument(
        "--disable-cache",
        action=argparse.BooleanOptionalAction,
        help="Disables the pip cache through the --no-cache-dir option",
    )

    args = p.parse_args(argv)

    # Validate arguments.
    if args.venv_dir.exists() and not args.venv_dir.is_dir():
        p.error(f"venv_dir '{args.venv_dir}' exists and is not a directory")

    run(args)


if __name__ == "__main__":
    main(sys.argv[1:])
