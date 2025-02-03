# therock_artifacts.cmake
# Facilities for bundling artifacts for bootstrapping and subsequent CI/CD
# phases.

function(therock_provide_artifact slice_name)
  cmake_parse_arguments(PARSE_ARGV 1 ARG
    "TARGET_NEUTRAL"
    "DESCRIPTOR"
    "COMPONENTS;SUBPROJECT_DEPS"
  )

  # Normalize arguments.
  set(_target_name "therock-artifact-${slice_name}")
  set(_archive_target_name "therock-archive-${slice_name}")
  if(TARGET "${_target_name}")
    message(FATAL_ERROR "Artifact slice '${slice_name}' provided more than once")
  endif()
  if(TARGET "${_archive_target_name}")
    message(FATAL_ERROR "Archive slice '${slice_name}' provided more than once")
  endif()

  if(NOT ARG_DESCRIPTOR)
    set(ARG_DESCRIPTOR "artifact.toml")
  endif()
  cmake_path(ABSOLUTE_PATH ARG_DESCRIPTOR BASE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}")

  # We make all artifact slices available as therock-artifacts top-level target.
  if(NOT TARGET therock-artifacts)
    add_custom_target(therock-artifacts)
  endif()
  if(NOT TARGET therock-archives)
    add_custom_target(therock-archives)
  endif()

  # Determine top-level name.
  if(ARG_TARGET_NEUTRAL)
    set(_bundle_name "any")
  else()
    set(_bundle_name "${THEROCK_AMDGPU_DIST_BUNDLE_NAME}")
  endif()
  set(_artifact_base_name "${slice_name}_${_bundle_name}")

  ### Generate artifact directories.
  # Determine dependencies.
  set(_stamp_file_deps)
  _therock_cmake_subproject_deps_to_stamp(_stamp_file_deps "stage.stamp" ${ARG_SUBPROJECT_DEPS})

  # Assemble commands.
  set(_fileset_tool "${THEROCK_SOURCE_DIR}/build_tools/fileset_tool.py")
  set(_command_list)
  set(_manifest_files)
  foreach(_component ${ARG_COMPONENTS})
    set(_component_dir "${THEROCK_BINARY_DIR}/artifacts/${_artifact_base_name}_${_component}")
    set(_manifest_file "${_component_dir}/artifact_manifest.txt")
    list(APPEND _manifest_files "${_manifest_file}")
    list(APPEND _command_list
      COMMAND "${Python3_EXECUTABLE}" "${_fileset_tool}" artifact
        --output-dir "${_component_dir}"
        --root-dir "${THEROCK_BINARY_DIR}" --descriptor "${ARG_DESCRIPTOR}"
        --component "${_component}"
        --manifest "${_manifest_file}"
    )
  endforeach()

  # Set up command.
  add_custom_command(
    OUTPUT ${_manifest_files}
    COMMENT "Merging artifact ${slice_name}"
    ${_command_list}
    DEPENDS
      ${_stamp_file_deps}
      "${ARG_DESCRIPTOR}"
      "${_fileset_tool}"
  )
  add_custom_target(
    "${_target_name}"
    DEPENDS ${_manifest_files}
  )
  add_dependencies(therock-artifacts "${_target_name}")

  ### Generate archives.
  set(_archive_files)
  foreach(_component ${ARG_COMPONENTS})
    foreach(_archive_type ${THEROCK_ARTIFACT_ARCHIVE_TYPES})
      set(_component_dir "${THEROCK_BINARY_DIR}/artifacts/${_artifact_base_name}_${_component}")
      set(_manifest_file "${_component_dir}/artifact_manifest.txt")
      set(_archive_file "${THEROCK_BINARY_DIR}/archives/${_artifact_base_name}_${_component}${THEROCK_ARTIFACT_ARCHIVE_SUFFIX}.${_archive_type}")
      list(APPEND _archive_files "${_archive_file}")
      set(_archive_sha_file "${_archive_file}.sha256sum")
      add_custom_command(
        OUTPUT
          "${_archive_file}"
          "${_archive_sha_file}"
        COMMENT "Creating archive ${_archive_file}"
        COMMAND
          "${Python3_EXECUTABLE}" "${_fileset_tool}"
          artifact-archive "${_component_dir}"
            -o "${_archive_file}" --type "${_archive_type}"
            --hash-file "${_archive_sha_file}" --hash-algorithm sha256
        DEPENDS
          "${_manifest_file}"
          "${_fileset_tool}"
      )
    endforeach()
  endforeach()

  add_custom_target("${_archive_target_name}" DEPENDS ${_archive_files})
  add_dependencies(therock-archives "${_archive_target_name}")
endfunction()
