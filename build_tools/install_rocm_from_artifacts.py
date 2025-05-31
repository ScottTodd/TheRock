#!/usr/bin/env python
"""install_rocm_from_artifacts.py

This script helps CI workflows, developers and testing suites easily install TheRock to their environment using artifacts.
It installs TheRock to an output directory from one of these sources:
- GitHub CI workflow run
- GitHub release tag
- An existing installation of TheRock

Usage:
python build_tools/install_rocm_from_artifacts.py [--output-dir OUTPUT_DIR] [--amdgpu-family AMDGPU_FAMILY] (--run-id RUN_ID | --release RELEASE | --input-dir INPUT_DIR)
                                        [--blas | --no-blas] [--fft | --no-fft] [--miopen | --no-miopen] [--prim | --no-prim]
                                        [--rand | --no-rand] [--rccl | --no-rccl] [--tests | --no-tests] [--base-only]

Examples:
- Downloads the gfx94X S3 artifacts from GitHub CI workflow run 14474448215 (from https://github.com/ROCm/TheRock/actions/runs/14474448215) to the default output directory `therock-build`:
    - `python build_tools/install_rocm_from_artifacts.py --run-id 14474448215 --amdgpu-family gfx94X-dcgpu --tests`
- Downloads the version `6.4.0rc20250416` gfx110X artifacts from GitHub release tag `nightly-tarball` to the specified output directory `build`:
    - `python build_tools/install_rocm_from_artifacts.py --release 6.4.0rc20250416 --amdgpu-family gfx110X-dgpu --output-dir build`
- Downloads the version `6.4.0.dev0+8f6cdfc0d95845f4ca5a46de59d58894972a29a9` gfx120X artifacts from GitHub release tag `dev-tarball` to the default output directory `therock-build`:
    - `python build_tools/install_rocm_from_artifacts.py --release 6.4.0.dev0+8f6cdfc0d95845f4ca5a46de59d58894972a29a9 --amdgpu-family gfx120X-all`

You can select your AMD GPU family from this file https://github.com/ROCm/TheRock/blob/59c324a759e8ccdfe5a56e0ebe72a13ffbc04c1f/cmake/therock_amdgpu_targets.cmake#L44-L81

By default for CI workflow retrieval, all artifacts (excluding test artifacts) will be downloaded. For specific artifacts, pass in the flag such as `--rand` (RAND artifacts) For test artifacts, pass in the flag `--tests` (test artifacts). For base artifacts only, pass in the flag `--base-only`

Note: the script will overwrite the output directory argument. If no argument is passed, it will overwrite the default "therock-build" directory.
"""

import argparse
from fetch_artifacts import (
    retrieve_base_artifacts,
    retrieve_enabled_artifacts,
    retrieve_s3_artifacts,
)
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
from _therock_utils.artifacts import ArtifactPopulator
from urllib.request import urlopen, Request


def log(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()


def _untar_files(output_dir, destination):
    """
    Retrieves all tar files in the output_dir, then extracts all files to the output_dir
    """
    log(f"Extracting {destination.name} to {str(output_dir)}")
    with tarfile.open(destination) as extracted_tar_file:
        extracted_tar_file.extractall(output_dir)
    destination.unlink()


def _create_output_directory(args):
    """
    If the output directory already exists, delete it and its contents.
    Then, create the output directory.
    """
    output_dir_path = args.output_dir
    log(f"Creating directory {output_dir_path}")
    if os.path.isdir(output_dir_path):
        log(
            f"Directory {output_dir_path} already exists, removing existing directory and files"
        )
        shutil.rmtree(output_dir_path)
    os.mkdir(output_dir_path)
    log(f"Created directory {output_dir_path}")


def _get_github_release_assets(release_tag, amdgpu_family, release_version):
    """
    Makes an API call to retrieve the release's assets, then retrieves the asset matching the amdgpu family
    """
    github_release_url = (
        f"https://api.github.com/repos/ROCm/TheRock/releases/tags/{release_tag}"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # If GITHUB_TOKEN environment variable is available, include it in the API request to avoid a lower rate limit
    gh_token = os.getenv("GITHUB_TOKEN", "")
    if gh_token:
        headers["Authentication"] = f"Bearer {gh_token}"

    request = Request(github_release_url, headers=headers)
    with urlopen(request) as response:
        if response.status == 403:
            log(
                f"Error when retrieving GitHub release assets for release tag '{release_tag}'. This is most likely a rate limiting issue, so please try again"
            )
            return
        elif response.status != 200:
            log(
                f"Error when retrieving GitHub release assets for release tag '{release_tag}' with status code {response.status}. Exiting..."
            )
            return

        release_data = json.loads(response.read().decode("utf-8"))

    # We retrieve the most recent release asset that matches the amdgpu_family
    # In the cases of "nightly-tarball" or "dev-tarball", this will retrieve the the specified version or latest
    asset_data = sorted(
        release_data["assets"], key=lambda item: item["updated_at"], reverse=True
    )

    # For nightly-tarball
    if release_tag == "nightly-tarball" and release_version != "latest":
        for asset in asset_data:
            if amdgpu_family in asset["name"] and release_version in asset["name"]:
                return asset
    # For dev-tarball
    elif release_tag == "dev-tarball":
        for asset in asset_data:
            if amdgpu_family in asset["name"] and release_version in asset["name"]:
                return asset
    # Otherwise, return the latest and amdgpu-matched asset available from the tag nightly-tarball
    elif release_tag == "nightly-tarball" and release_version == "latest":
        for asset in asset_data:
            if amdgpu_family in asset["name"]:
                return asset

    return None


def _download_github_release_asset(asset_data, output_dir):
    """
    With the GitHub asset data, this function downloads the asset to the output_dir
    """
    asset_name = asset_data["name"]
    asset_url = asset_data["url"]
    destination = output_dir / asset_name
    headers = {"Accept": "application/octet-stream"}
    # Making the API call to retrieve the asset
    request = Request(asset_url, headers=headers)

    with urlopen(request) as response_obj, open(destination, "wb") as file:
        # Downloading the asset to destination
        log(f"Downloading tar file to {str(destination)}")
        shutil.copyfileobj(response_obj, file)

    # After downloading the asset, untar-ing the file
    _untar_files(output_dir, destination)


def retrieve_artifacts_by_run_id(args):
    """
    If the user requested TheRock artifacts by CI (run ID), this function will retrieve those assets
    """
    run_id = args.run_id
    output_dir = args.output_dir
    amdgpu_family = args.amdgpu_family
    log(f"Retrieving artifacts for run ID {run_id}")
    s3_artifacts = retrieve_s3_artifacts(run_id, amdgpu_family)

    # Retrieving base and all math-lib tar artifacts and downloading them to output_dir
    retrieve_base_artifacts(args, run_id, output_dir, s3_artifacts)
    if not args.base_only:
        retrieve_enabled_artifacts(
            args, amdgpu_family, run_id, output_dir, s3_artifacts
        )

    # Flattening artifacts from .tar* files then removing .tar* files
    log(f"Untar-ing artifacts for {run_id}")
    tar_file_paths = list(output_dir.glob("*.tar.*"))
    flattener = ArtifactPopulator(output_path=output_dir, verbose=True, flatten=True)
    flattener(*tar_file_paths)
    for file_path in tar_file_paths:
        # TODO: keep the original files in a temp/cache dir to avoid redownloading on re-run?
        # TODO: Log when deleting
        file_path.unlink()

    log(f"Retrieved artifacts for run ID {run_id}")


def retrieve_artifacts_by_release(args):
    """
    If the user requested TheRock artifacts by release version, this function will retrieve those assets
    """
    output_dir = args.output_dir
    amdgpu_family = args.amdgpu_family
    # In the case that the user passes in latest, we will get the latest nightly-tarball
    if args.release == "latest":
        release_tag = "nightly-tarball"
    # Otherwise, determine if version is nightly-tarball or dev-tarball
    else:
        # Searching for nightly-tarball or dev-tarball format
        nightly_regex_expression = (
            "(\\d+\\.)?(\\d+\\.)?(\\*|\\d+)rc(\\d{4})(\\d{2})(\\d{2})"
        )
        dev_regex_expression = "(\\d+\\.)?(\\d+\\.)?(\\*|\\d+).dev0+"
        nightly_release = re.search(nightly_regex_expression, args.release) != None
        dev_release = re.search(dev_regex_expression, args.release) != None
        if not nightly_release and not dev_release:
            log("This script requires a nightly-tarball or dev-tarball version.")
            log("Please retrieve the correct release version from:")
            log(
                "\t - https://github.com/ROCm/TheRock/releases/tag/nightly-tarball (nightly-tarball example: 6.4.0rc20250416)"
            )
            log(
                "\t - https://github.com/ROCm/TheRock/releases/tag/dev-tarball (dev-tarball example: 6.4.0.dev0+8f6cdfc0d95845f4ca5a46de59d58894972a29a9)"
            )
            log("Exiting...")
            return

        release_tag = "nightly-tarball" if nightly_release else "dev-tarball"
    release_version = args.release

    log(f"Retrieving artifacts for release tag {release_tag}")
    asset_data = _get_github_release_assets(release_tag, amdgpu_family, release_version)
    if not asset_data:
        log(f"GitHub release asset for '{release_tag}' not found. Exiting...")
        return
    _download_github_release_asset(asset_data, output_dir)
    log(f"Retrieving artifacts for run ID {release_tag}")


def retrieve_artifacts_by_input_dir(args):
    input_dir = args.input_dir
    output_dir = args.output_dir
    log(f"Retrieving artifacts from input dir {input_dir}")

    # Check to make sure rsync exists
    if not shutil.which("rsync"):
        log("Error: rsync command not found.")
        if platform.system() == "Windows":
            log("Please install rsync via MSYS2 or WSL to your Windows system")
        return

    cmd = [
        "rsync",
        "-azP",  # archive, compress and progress indicator
        input_dir,
        output_dir,
    ]
    try:
        subprocess.run(cmd, check=True)
        log(f"Retrieved artifacts from input dir {input_dir} to {output_dir}")
    except Exception as ex:
        # rsync is not available
        log(f"Error when running [{cmd}]")
        log(str(ex))


def run(args):
    log("### Installing TheRock using artifacts ###")
    _create_output_directory(args)
    if args.run_id:
        retrieve_artifacts_by_run_id(args)
    elif args.release:
        retrieve_artifacts_by_release(args)

    if args.input_dir:
        retrieve_artifacts_by_input_dir(args)


def main(argv):
    parser = argparse.ArgumentParser(prog="provision")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="./therock-build",
        help="Path of the output directory for TheRock",
    )

    parser.add_argument(
        "--amdgpu-family",
        type=str,
        default="gfx94X-dcgpu",
        help="AMD GPU family to install (please refer to this: https://github.com/ROCm/TheRock/blob/59c324a759e8ccdfe5a56e0ebe72a13ffbc04c1f/cmake/therock_amdgpu_targets.cmake#L44-L81 for family choices)",
    )

    # This mutually exclusive group will ensure that only one argument is present
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-id", type=str, help="GitHub run ID of TheRock to install")

    group.add_argument(
        "--release",
        type=str,
        help="Github release version of TheRock to install, from the nightly-tarball (X.Y.ZrcYYYYMMDD) or dev-tarball (X.Y.Z.dev0+{hash})",
    )

    artifacts_group = parser.add_argument_group("artifacts_group")
    artifacts_group.add_argument(
        "--blas",
        default=False,
        help="Include 'blas' artifacts",
        action=argparse.BooleanOptionalAction,
    )

    artifacts_group.add_argument(
        "--fft",
        default=False,
        help="Include 'fft' artifacts",
        action=argparse.BooleanOptionalAction,
    )

    artifacts_group.add_argument(
        "--miopen",
        default=False,
        help="Include 'miopen' artifacts",
        action=argparse.BooleanOptionalAction,
    )

    artifacts_group.add_argument(
        "--prim",
        default=False,
        help="Include 'prim' artifacts",
        action=argparse.BooleanOptionalAction,
    )

    artifacts_group.add_argument(
        "--rand",
        default=False,
        help="Include 'rand' artifacts",
        action=argparse.BooleanOptionalAction,
    )

    artifacts_group.add_argument(
        "--rccl",
        default=False,
        help="Include 'rccl' artifacts",
        action=argparse.BooleanOptionalAction,
    )

    artifacts_group.add_argument(
        "--tests",
        default=False,
        help="Include all test artifacts for enabled libraries",
        action=argparse.BooleanOptionalAction,
    )

    artifacts_group.add_argument(
        "--dev",
        default=False,
        help="Include all dev artifacts for enabled libraries",
        action=argparse.BooleanOptionalAction,
    )

    artifacts_group.add_argument(
        "--base-only", help="Include only base artifacts", action="store_true"
    )

    group.add_argument(
        "--input-dir",
        type=str,
        help="Pass in an existing directory of TheRock to provision and test",
    )

    args = parser.parse_args(argv)
    run(args)


if __name__ == "__main__":
    main(sys.argv[1:])
