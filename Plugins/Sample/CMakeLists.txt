cmake_minimum_required(VERSION 3.14)

project(PeelCapSamplePlugin)

# Plugin DLL
add_library(PeelCapSamplePlugin SHARED dllmain.cpp ${CMAKE_CURRENT_LIST_DIR}/../peelCapPlugin.h )

target_include_directories(PeelCapSamplePlugin PUBLIC  
	${CMAKE_CURRENT_SOURCE_DIR}
	${CMAKE_CURRENT_SOURCE_DIR}/..)

set_target_properties(PeelCapSamplePlugin PROPERTIES PREFIX "")
set_target_properties(PeelCapSamplePlugin PROPERTIES OUTPUT_NAME "PeelCapSamplePlugin")
target_compile_definitions(PeelCapSamplePlugin PUBLIC -DPEEL_PLUGIN_EXPORTS)

if(TARGET PeelCapture)
add_custom_command(
    TARGET PeelCapSamplePlugin POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:PeelCapSamplePlugin> $<TARGET_FILE_DIR:PeelCapture>/plugins
    COMMENT "Copying example plugin to app build dir"
)
endif()
