# MIOpen uses find_path, which is a pretty poor way to get this.
# TODO: Fix this upstream and remove this hack.
include_directories("${THEROCK_BINARY_DIR}/base/half/stage/include")
list(APPEND CMAKE_SYSTEM_INCLUDE_PATH "${THEROCK_BINARY_DIR}/base/half/stage/include")

# TODO: hipblas does not appear to be setting its include directory when used
# in an isolated directory via find_package (this has probably been masked when
# in a directory with everything else). So we just include it here.
# Fix upstream and remove this.
include_directories("${THEROCK_BINARY_DIR}/math-libs/hipBLAS/stage/include")

# TODO: Ditto for hipBLAS-common
include_directories("${THEROCK_BINARY_DIR}/math-libs/hipBLAS-common/stage/include")

# TODO: Ditto for rocrand
include_directories("${THEROCK_BINARY_DIR}/math-libs/rocRAND/stage/include")
