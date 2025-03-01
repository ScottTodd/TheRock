if(THEROCK_ENABLE_CORE_RUNTIME)
  ##############################################################################
  # ROCR-Runtime
  ##############################################################################

  therock_cmake_subproject_declare(ROCR-Runtime
    EXTERNAL_SOURCE_DIR "ROCR-Runtime"
    BACKGROUND_BUILD
    CMAKE_ARGS
      "-DBUILD_SHARED_LIBS=ON"
    BUILD_DEPS
      amd-llvm
    RUNTIME_DEPS
      rocprofiler-register
    INTERFACE_LINK_DIRS
      "lib"
  )
  therock_cmake_subproject_glob_c_sources(ROCR-Runtime
    SUBDIRS
      libhsakmt
      runtime
  )
  therock_cmake_subproject_provide_package(ROCR-Runtime hsakmt lib/cmake/hsakmt)
  therock_cmake_subproject_provide_package(ROCR-Runtime hsa-runtime64 lib/cmake/hsa-runtime64)
  therock_cmake_subproject_activate(ROCR-Runtime)

  ##############################################################################
  # rocminfo
  ##############################################################################

  therock_cmake_subproject_declare(rocminfo
    EXTERNAL_SOURCE_DIR "rocminfo"
    BACKGROUND_BUILD
    RUNTIME_DEPS
      ROCR-Runtime
  )
  therock_cmake_subproject_glob_c_sources(rocminfo SUBDIRS .)
  therock_cmake_subproject_activate(rocminfo)

  therock_provide_artifact(core-runtime
    TARGET_NEUTRAL
    DESCRIPTOR artifact-core-runtime.toml
    COMPONENTS
      dbg
      dev
      doc
      lib
      run
    SUBPROJECT_DEPS
      ROCR-Runtime
      rocminfo
  )

endif(THEROCK_ENABLE_CORE_RUNTIME)

if(THEROCK_ENABLE_HIP_RUNTIME)
  ##############################################################################
  # clr
  # The primary HIP compiler and runtime target. This is also the project used
  # to root the "amd-hip" compiler toolchain and is a superset of amd-llvm.
  # As a particularly sharp edge, the `hipconfig` tool is really only fully
  # functional from this project (which contributes version and metadata).
  ##############################################################################

  therock_cmake_subproject_declare(hip-clr
    EXTERNAL_SOURCE_DIR "clr"
    INTERFACE_PROGRAM_DIRS
      bin
    BACKGROUND_BUILD
    CMAKE_ARGS
      -DHIP_PLATFORM=amd
      "-DHIP_COMMON_DIR=${CMAKE_CURRENT_SOURCE_DIR}/HIP"
      -DCLR_BUILD_OCL=OFF
      -DCLR_BUILD_HIP=ON
      # Legacy: Disable various auto-detection logic that breaks out of jail
      # and can use local machine tools.
      -DHIPCC_BIN_DIR=

      # TODO:
      # [build] [hip-clr configure] CMake Error at rocclr/cmake/ROCclr.cmake:47 (add_library):
      # [build] [hip-clr configure]   add_library cannot create target "rocclr" because another target with the
      # [build] [hip-clr configure]   same name already exists.  The existing target is a static library created
      # [build] [hip-clr configure]   in source directory "D:/projects/TheRock/core/clr/rocclr".  See
      # [build] [hip-clr configure]   documentation for policy CMP0002 for more details.

      # ==================================
      # Windows-specific options
      -DUSE_PROF_API=OFF
      -DROCCLR_ENABLE_HSAIL=OFF
      -DROCCLR_ENABLE_LC=ON
      -DROCCLR_ENABLE_HSA=OFF
      -DROCCLR_ENABLE_PAL=ON

      # TODO: set this as needed by FindAMD_PAL.cmake
      # -DAMD_DRIVERS_PATH=

      # TODO: import PAL into sources
      -DAMD_SC_PATH=D:/projects/pal/src/core/imported/hsa

      # Disable pre-compiled hip headers (may be possible to use, but requires some toolchain / deps setup)
      -D__HIP_ENABLE_PCH=OFF

      -DPAL_CLOSED_SOURCE=OFF
      # ==================================
    BUILD_DEPS
      rocm-cmake
    RUNTIME_DEPS
      amd-llvm
      amd-comgr
      hipcc     # For hipconfig
      # rocm-core
      # rocminfo  # Various things expect to be able to find the rocminfo tools
      rocprofiler-register

      # -----------------------------------------------------------------------
      # This may be needed for some header files... or not. TBD. Probably not
      # needed as a full runtime or build dep at least?
      # For example:
      #   `core/clr/rocclr/device/pal/palprogram.cpp` wants `amd_hsa_loader.hpp`
      #   A version of that file is available at
      #   `core/ROCR-Runtime/runtime/hsa-runtime/core/inc/amd_hsa_loader.hpp`
      #   Another public source is under
      #   https://github.com/HSAFoundation/HSA-Runtime-Reference-Source/
      #   This header can also come from the closed source HSAIL compiler, but
      #   we build CLR with the LC (amd-llvm/amd-comgr) compiler, not HSAIL
      #
      # See also `core/clr/rocclr/FindAMD_HSA_LOADER.cmake`
      # -----------------------------------------------------------------------
      # ROCR-Runtime
    INTERFACE_LINK_DIRS
      "lib"
  )
  therock_cmake_subproject_glob_c_sources(hip-clr SUBDIRS .)
  therock_cmake_subproject_provide_package(hip-clr hip lib/cmake/hip)
  # TODO: Some projects resolve "hip" vs "HIP" so we advertise both, but this isn't
  # great.
  therock_cmake_subproject_provide_package(hip-clr HIP lib/cmake/hip)
  therock_cmake_subproject_provide_package(hip-clr hip-lang lib/cmake/hip-lang)
  therock_cmake_subproject_provide_package(hip-clr hiprtc lib/cmake/hiprtc)
  therock_cmake_subproject_activate(hip-clr)


  therock_provide_artifact(core-hip
    TARGET_NEUTRAL
    DESCRIPTOR artifact-core-hip.toml
    COMPONENTS
      dbg
      dev
      doc
      lib
      run
    SUBPROJECT_DEPS
      hip-clr
  )
endif(THEROCK_ENABLE_HIP_RUNTIME)
