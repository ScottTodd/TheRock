import ast
import configparser
import os
import platform
import sys
from lib_python.repo_management import RockProjectRepo
from pathlib import Path, PurePosixPath


class RockProjectBuilder(configparser.ConfigParser):
    def __init__(self, rock_builder_root_dir, project_name):
        super(RockProjectBuilder, self).__init__(allow_no_value=True)

        self.is_posix = not any(platform.win32_ver())
        self.project_name = project_name
        self.cfg_file_path = (
            Path(rock_builder_root_dir) / "projects" / f"{project_name}.cfg"
        )
        if self.cfg_file_path.exists():
            self.read(self.cfg_file_path)
        else:
            raise ValueError(
                "Could not find the configuration file: "
                + self.cfg_file_path.as_posix()
            )
        self.repo_url = self.get("project_info", "repo_url")
        self.project_version = self.get("project_info", "version")

        # environment setup can have common and os-specific sections that needs to be appended together
        self.skip_on_os = None
        try:
            if self.is_posix:
                self.skip_on_os = self.get("project_info", "skip_linux")
            else:
                self.skip_on_os = self.get("project_info", "skip_windows")
        except Exception as ex1:
            pass
        self.env_setup_cmd = None
        try:
            value = self.get("project_info", "env_common")
            self.env_setup_cmd = list(
                filter(None, (x.strip() for x in value.splitlines()))
            )
        except:
            pass
        try:
            if self.is_posix:
                value = self.get("project_info", "env_linux")
                temp_env_list = list(
                    filter(None, (x.strip() for x in value.splitlines()))
                )
            else:
                value = self.get("project_info", "env_windows")
                temp_env_list = list(
                    filter(None, (x.strip() for x in value.splitlines()))
                )
            if self.env_setup_cmd:
                self.env_setup_cmd.extend(temp_env_list)
            else:
                self.env_setup_cmd = temp_env_list
        except:
            pass
        try:
            self.init_cmd = self.get("project_info", "init_cmd")
        except:
            self.init_cmd = None
        try:
            self.clean_cmd = self.get("project_info", "clean_cmd")
        except:
            self.clean_cmd = None
        try:
            self.hipify_cmd = self.get("project_info", "hipify_cmd")
        except:
            self.hipify_cmd = None
        try:
            self.pre_config_cmd = self.get("project_info", "pre_config_cmd")
        except:
            self.pre_config_cmd = None
        try:
            self.config_cmd = self.get("project_info", "config_cmd")
        except:
            self.config_cmd = None
        try:
            self.post_config_cmd = self.get("project_info", "post_config_cmd")
        except:
            self.post_config_cmd = None
        try:
            build_cmd = None
            is_windows = any(platform.win32_ver())
            if is_windows and self.has_option("project_info", "build_cmd_windows"):
                self.build_cmd = self.get("project_info", "build_cmd_windows")
            else:
                self.build_cmd = self.get("project_info", "build_cmd")
            print("Build_cmd: ------------")
            print(self.build_cmd)
            print("------------------------")
        except Exception as ex1:
            print(ex1)
            self.build_cmd = None
        try:
            self.cmake_config = self.get("project_info", "cmake_config")
        except:
            self.cmake_config = None
        try:
            self.install_cmd = self.get("project_info", "install_cmd")
        except:
            self.install_cmd = None
        try:
            self.post_install_cmd = self.get("project_info", "post_install_cmd")
        except:
            self.post_install_cmd = None
        self.project_root_dir_path = Path(rock_builder_root_dir)
        self.project_src_dir_path = (
            Path(rock_builder_root_dir) / "src_projects" / self.project_name
        )
        self.project_build_dir_path = (
            Path(rock_builder_root_dir) / "builddir" / self.project_name
        )
        try:
            self.cmd_execution_dir = self.get("project_info", "cmd_exec_dir")
        except:
            # default value if not specified in the config-file
            self.cmd_execution_dir = self.project_src_dir_path
        self.project_patch_dir_root = (
            Path(rock_builder_root_dir)
            / "../../external-builds/pytorch/patches"
            / self.project_name
        )
        self.project_patch_dir_root = self.project_patch_dir_root.resolve()
        self.project_repo = RockProjectRepo(
            self.project_name,
            self.project_root_dir_path,
            self.project_src_dir_path,
            self.project_build_dir_path,
            self.cmd_execution_dir,
            self.repo_url,
            self.project_version,
            self.project_patch_dir_root,
        )

    # printout project builder specific info for logging and debug purposes
    def printout(self, phase):
        print("Project build phase " + phase + ": -----")
        print("    Project_name: " + self.project_name)
        print("    Config_path: " + self.cfg_file_path.as_posix())
        print("    Version:     " + self.project_version)
        print("    Source_dir:  " + self.project_src_dir_path.as_posix())
        print("    Patch_dir:   " + self.project_patch_dir_root.as_posix())
        print("    Build_dir:   " + self.project_build_dir_path.as_posix())
        print("------------------------")

    def printout_error_and_terminate(self, phase):
        self.printout(phase)
        print(phase + " failed")
        sys.exit(1)

    # check whether operations should be skipped on current operating system
    def check_skip_on_os(self):
        ret = True
        if (self.skip_on_os is None) or (
            (self.skip_on_os != "1")
            and (str(self.skip_on_os).casefold() != str("y").casefold())
            and (str(self.skip_on_os).casefold() != str("yes").casefold())
            and (str(self.skip_on_os).casefold() != str("on").casefold())
        ):
            ret = False
        return ret

    def do_env_setup(self):
        res = self.project_repo.do_env_setup(self.env_setup_cmd)
        if not res:
            self.printout_error_and_terminate("env_setup")

    def undo_env_setup(self):
        res = self.project_repo.undo_env_setup(self.env_setup_cmd)
        if not res:
            self.printout_error_and_terminate("undo_env_setup")

    def init(self):
        res = self.project_repo.do_init(self.init_cmd)
        if not res:
            self.printout_error_and_terminate("init")

    def clean(self):
        res = self.project_repo.do_clean(self.clean_cmd)
        if not res:
            self.printout_error_and_terminate("clean")

    def checkout(self):
        res = self.project_repo.do_checkout()
        if not res:
            self.printout_error_and_terminate("checkout")

    def hipify(self):
        res = self.project_repo.do_hipify(self.hipify_cmd)
        if not res:
            self.printout_error_and_terminate("hipify")

    def pre_config(self):
        res = self.project_repo.do_pre_config(self.pre_config_cmd)
        if not res:
            self.printout_error_and_terminate("pre_config")

    def config(self):
        if self.cmake_config:
            # in case that project has cmake configure/build/install needs
            res = self.project_repo.do_cmake_config(self.cmake_config)
            if not res:
                self.printout_error_and_terminate("cmake_config")
        res = self.project_repo.do_config(self.config_cmd)
        if not res:
            self.printout_error_and_terminate("config")

    def post_config(self):
        res = self.project_repo.do_post_config(self.post_config_cmd)
        if not res:
            self.printout_error_and_terminate("post_config")

    def build(self):
        if self.cmake_config:
            # not all projects have things to build with cmake
            res = self.project_repo.do_cmake_build(self.cmake_config)
            if not res:
                self.printout_error_and_terminate("cmake_build")
        res = self.project_repo.do_build(self.build_cmd)
        if not res:
            self.printout_error_and_terminate("build")

    def install(self):
        if self.cmake_config:
            res = self.project_repo.do_cmake_install(self.cmake_config)
            if not res:
                self.printout_error_and_terminate("cmake_install")
        res = self.project_repo.do_install(self.install_cmd)
        if not res:
            self.printout_error_and_terminate("install")

    def post_install(self):
        res = self.project_repo.do_post_install(self.post_install_cmd)
        if not res:
            self.printout_error_and_terminate("post_install")


class RockExternalProjectListManager(configparser.ConfigParser):
    def __init__(self, rock_builder_root_dir):
        # default application list to builds
        self.cfg_file_path = Path(rock_builder_root_dir) / "projects" / "core_apps.pcfg"
        self.rock_builder_root_dir = rock_builder_root_dir
        super(RockExternalProjectListManager, self).__init__(allow_no_value=True)
        if self.cfg_file_path.exists():
            self.read(self.cfg_file_path)

    def get_external_project_list(self):
        value = self.get("projects", "project_list")
        # convert to list of project string names
        return list(filter(None, (x.strip() for x in value.splitlines())))

    def get_rock_project_builder(self, project_name):
        ret = None
        try:
            ret = RockProjectBuilder(self.rock_builder_root_dir, project_name)
        except ValueError as e:
            print(str(e))
        return ret
