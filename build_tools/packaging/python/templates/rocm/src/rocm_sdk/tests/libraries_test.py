"""Test of the library trees."""

"""Installation package tests for the core package."""

import importlib
from pathlib import Path
import subprocess
import sys
import sysconfig
import unittest

from .. import _dist_info as di
from . import utils

import rocm_sdk

utils.assert_is_physical_package(rocm_sdk)

libraries_mod_name = di.ALL_PACKAGES["libraries"].get_py_package_name(
    target_family=di.determine_target_family()
)
libraries_mod = importlib.import_module(libraries_mod_name)
utils.assert_is_physical_package(libraries_mod)

so_paths = utils.get_module_shared_libraries(libraries_mod)

CONSOLE_SCRIPT_TESTS = []


class ROCmLibrariesTest(unittest.TestCase):
    def testInstallationLayout(self):
        """The `rocm_sdk` and libraries module must be siblings on disk."""
        sdk_path = Path(rocm_sdk.__file__)
        self.assertEqual(
            sdk_path.name,
            "__init__.py",
            msg="Expected `rocm_sdk` module to be a non-namespace package",
        )
        libraries_path = Path(libraries_mod.__file__)
        self.assertEqual(
            libraries_path.name,
            "__init__.py",
            msg=f"Expected `{libraries_mod_name}` module to be a non-namespace package",
        )
        self.assertEqual(
            sdk_path.parent.parent,
            libraries_path.parent.parent,
            msg="Paths are not siblings",
        )

    def testSharedLibrariesLoad(self):
        self.assertTrue(
            so_paths, msg="Expected core package to contain shared libraries"
        )

        for so_path in so_paths:
            with self.subTest(msg="Check shared library loads", so_path=so_path):
                # Load each in an isolated process because not all libraries in the tree
                # are designed to load into the same process (i.e. LLVM runtime libs,
                # etc).
                command = "import ctypes; import sys; ctypes.CDLL(sys.argv[1])"
                subprocess.check_call(
                    [sys.executable, "-P", "-c", command, str(so_path)]
                )

    def testConsoleScripts(self):
        scripts_path = Path(sysconfig.get_path("scripts"))
        for script_name, cl, expected_text, required in CONSOLE_SCRIPT_TESTS:
            script_path = scripts_path / script_name
            if not required and not script_path.exists():
                continue
            with self.subTest(msg=f"Check console-script {script_name}"):
                self.assertTrue(
                    script_path.exists(),
                    msg=f"Console script {script_path} does not exist",
                )
                output_text = subprocess.check_output(
                    [script_path] + cl, stderr=sys.stdout
                ).decode()
                if expected_text not in output_text:
                    self.fail(
                        f"Expected '{expected_text}' in console-script {script_name} outuput:\n"
                        f"{output_text}"
                    )
