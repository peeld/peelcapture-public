cmake_minimum_required(VERSION 3.1)

project(PeelCapSamplePlugin)

# Plugin DLL
add_library(PeelCapSamplePlugin SHARED dllmain.cpp ${CMAKE_CURRENT_LIST_DIR}/../peelCapPlugin.h )

target_include_directories(PeelCapSamplePlugin PUBLIC  
	${CMAKE_CURRENT_SOURCE_DIR}
	${CMAKE_CURRENT_SOURCE_DIR}/..)

set_target_properties(PeelCapSamplePlugin PROPERTIES PREFIX "")
set_target_properties(PeelCapSamplePlugin PROPERTIES OUTPUT_NAME "PeelCapSamplePlugin")
target_compile_definitions(PeelCapSamplePlugin PUBLIC -DPEEL_PLUGIN_EXPORTS)
