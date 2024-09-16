cmake_minimum_required(VERSION 3.14)

set(PluginName "MotivePlugin")

project(${PluginName})

# Plugin DLL
add_library(${PluginName} SHARED motivePlugin.cpp motivePlugin.h ${CMAKE_CURRENT_LIST_DIR}/../peelCapPlugin.h  )

target_include_directories(${PluginName} PUBLIC 
	${CMAKE_CURRENT_SOURCE_DIR}
	${CMAKE_CURRENT_SOURCE_DIR}/..
	${CMAKE_CURRENT_LIST_DIR}/MocapApi/include
	)

#if(EXISTS ${natnet_dir})
#set(natnet_dir "D:/BUILD/source/natnetsdk")
#endif()


target_include_directories(${PluginName} PUBLIC "${natnet_dir}/windows/include")
target_link_libraries(${PluginName} PUBLIC "${natnet_dir}/windows/lib/x64/NatNetLib.lib")
set_target_properties(${PluginName} PROPERTIES PREFIX "")
set_target_properties(${PluginName} PROPERTIES OUTPUT_NAME ${PluginName})
target_compile_definitions(${PluginName} PUBLIC -DPEEL_PLUGIN_EXPORTS)


if(TARGET PeelCapture)

	add_custom_command(TARGET ${PluginName} POST_BUILD 
		COMMAND ${CMAKE_COMMAND} -E copy "${natnet_dir}/windows/lib/x64/NatNetLib.dll"
		$<TARGET_FILE_DIR:PeelCapture>/NatNetLib.dll)

	add_custom_command(TARGET ${PluginName} POST_BUILD
		COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:${PluginName}>  $<TARGET_FILE_DIR:PeelCapture>/plugins)

endif()
