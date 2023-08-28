cmake_minimum_required(VERSION 3.1)

project(CapturyPlugin)

# Plugin DLL
add_library(CapturyPlugin SHARED dllmain.cpp ${CMAKE_CURRENT_LIST_DIR}/../peelCapPlugin.h  )

target_include_directories(CapturyPlugin PUBLIC 
	${CMAKE_CURRENT_SOURCE_DIR}
	${CMAKE_CURRENT_SOURCE_DIR}/..
	${CMAKE_CURRENT_LIST_DIR}/include
	)

set_target_properties(CapturyPlugin PROPERTIES PREFIX "")
set_target_properties(CapturyPlugin PROPERTIES OUTPUT_NAME "CapturyPlugin")
target_compile_definitions(CapturyPlugin PUBLIC -DPEEL_PLUGIN_EXPORTS)

#add_custom_command(TARGET AxisPlugin POST_BUILD
#    COMMAND ${CMAKE_COMMAND} -E copy 
#		$<TARGET_FILE:AxisPlugin> 
#		${CMAKE_CURRENT_BINARY_DIR}/$<TARGET_FILE_NAME:AxisPlugin> )


	add_custom_command(TARGET CapturyPlugin POST_BUILD 
		COMMAND ${CMAKE_COMMAND} -E copy 
		${CMAKE_CURRENT_LIST_DIR}/MocapApi/bin/win32/x64/release/MocapApi.dll 
		$<TARGET_FILE_DIR:Controller>/MocapApi.dll)

	add_custom_command(TARGET AxisPlugin POST_BUILD
		COMMAND ${CMAKE_COMMAND} -E copy 
			$<TARGET_FILE:AxisPlugin> 
			$<TARGET_FILE_DIR:Controller>/plugins/$<TARGET_FILE_NAME:AxisPlugin> )
