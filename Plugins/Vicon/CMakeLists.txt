cmake_minimum_required(VERSION 3.14)

set(PluginName "ViconPlugin")

project(${PluginName})

# Plugin DLL
add_library(${PluginName} SHARED viconPlugin.cpp viconPlugin.h ${CMAKE_CURRENT_LIST_DIR}/../peelCapPlugin.h  )

target_include_directories(${PluginName} PUBLIC 
	${CMAKE_CURRENT_SOURCE_DIR}
	${CMAKE_CURRENT_SOURCE_DIR}/..
	${CMAKE_CURRENT_LIST_DIR}/MocapApi/include
	)

if(EXISTS ${CMAKE_CURRENT_LIST_DIR}/../../../vicon-datastream/Win64/CPP)
set(vicon_dir "${CMAKE_CURRENT_LIST_DIR}/../../../vicon-datastream/Win64/CPP")
endif()


target_include_directories(${PluginName} PUBLIC ${vicon_dir})
target_link_libraries(${PluginName} PUBLIC ${vicon_dir}/ViconDataStreamSDK_CPP.lib)
set_target_properties(${PluginName} PROPERTIES PREFIX "")
set_target_properties(${PluginName} PROPERTIES OUTPUT_NAME ${PluginName})
target_compile_definitions(${PluginName} PUBLIC -DPEEL_PLUGIN_EXPORTS)


if(TARGET PeelCapture)

	file(GLOB files "${vicon_dir}/*.dll")
	foreach(file ${files})
	add_custom_command(TARGET ${PluginName} POST_BUILD 
		COMMAND ${CMAKE_COMMAND} -E copy ${file}
		$<TARGET_FILE_DIR:PeelCapture>/)

	endforeach()

	add_custom_command(TARGET ${PluginName} POST_BUILD
		COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:${PluginName}>  $<TARGET_FILE_DIR:PeelCapture>/plugins)

endif()
