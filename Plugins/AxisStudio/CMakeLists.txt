cmake_minimum_required(VERSION 3.1)

project(AxisStudioPlugin)

# Plugin DLL
add_library(AxisPlugin SHARED dllmain.cpp ${CMAKE_CURRENT_LIST_DIR}/../peelCapPlugin.h  )

target_include_directories(AxisPlugin PUBLIC 
	${CMAKE_CURRENT_SOURCE_DIR}
	${CMAKE_CURRENT_SOURCE_DIR}/..
	${CMAKE_CURRENT_LIST_DIR}/MocapApi/include
	)

target_link_libraries(AxisPlugin PUBLIC ${CMAKE_CURRENT_LIST_DIR}/MocapApi/lib/win32/x64/MocapApi.lib)
set_target_properties(AxisPlugin PROPERTIES PREFIX "")
set_target_properties(AxisPlugin PROPERTIES OUTPUT_NAME "AxisPlugin")
target_compile_definitions(AxisPlugin PUBLIC -DPEEL_PLUGIN_EXPORTS)

#add_custom_command(TARGET AxisPlugin POST_BUILD
#    COMMAND ${CMAKE_COMMAND} -E copy 
#		$<TARGET_FILE:AxisPlugin> 
#		${CMAKE_CURRENT_BINARY_DIR}/$<TARGET_FILE_NAME:AxisPlugin> )
