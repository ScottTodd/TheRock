#!/usr/bin/bash

set -eox pipefail

SCRIPT_DIR="$(cd $(dirname $0) && pwd)"

if ! source $SCRIPT_DIR/env_init.sh; then
	echo "Failed to find python virtual-env"
	echo "Make sure that TheRock has been build first"
        exit 1
fi

BUILD_DIR_ROOT=$ROCM_HOME/../..

# Environment variables recommended here:
# https://github.com/ROCm/TheRock/discussions/409#discussioncomment-13032345
export USE_ROCM=ON
export USE_KINETO=0
export BUILD_TEST=0
export USE_FLASH_ATTENTION=0
export USE_MEM_EFF_ATTENTION=0
export CMAKE_PREFIX_PATH="$ROCM_HOME"
# export HIP_CLANG_PATH="$ROCM_HOME/bin"
export HIP_CLANG_PATH="$ROCM_HOME/lib/llvm/bin"
export CC=clang-cl
export CXX=clang-cl
export DISTUTILS_USE_SDK=1

# match this with `-DTHEROCK_AMDGPU_FAMILIES` used to bulid TheRock
export PYTORCH_ROCM_ARCH=gfx1100
# export PYTORCH_ROCM_ARCH=gfx1151

# Copy some files over.
# TODO: see if these get installed once my build with tests enabled completes.
# cp $BUILD_DIR_ROOT/math-libs/BLAS/hipBLASLt/dist/bin/hipblaslt-bench.exe $ROCM_HOME/bin
# cp $BUILD_DIR_ROOT/math-libs/BLAS/hipBLASLt/dist/bin/hipblaslt-test.exe $ROCM_HOME/bin

cd src
# python setup.py develop
python setup.py bdist_wheel
# python setup.py --help-commands
