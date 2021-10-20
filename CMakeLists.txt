cmake_minimum_required(VERSION 3.0)
project(xtrace)

set(EXTERNAL_INSTALL_LOCATION ${CMAKE_CURRENT_SOURCE_DIR})

if(NOT DEFINED CMAKE_INSTALL_PREFIX)
	set(CMAKE_INSTALL_PREFIX ${CMAKE_CURRENT_SOURCE_DIR})
	message("Install Current Directory: ${CMAKE_INSTALL_PREFIX}")
else()
	message("Install At ${CMAKE_INSTALL_PREFIX}")
endif()

include(ExternalProject)


find_program(LSB_RELEASE_EXEC lsb_release)
execute_process(COMMAND ${LSB_RELEASE_EXEC} -is
		OUTPUT_VARIABLE LSB_RELEASE_ID_SHORT
		OUTPUT_STRIP_TRAILING_WHITESPACE
)

if((${LSB_RELEASE_ID_SHORT} MATCHES "CentOS") OR (${LSB_RELEASE_ID_SHORT} MATCHES "RedHatEnterpriseServer"))
		LINK_DIRECTORIES(${CMAKE_CURRENT_SOURCE_DIR}/lib /usr/lib /lib64 /lib /usr/lib64)
endif()

if ( MSVC )
	message("-- cstrace for Windows is not provided, SKIPPED")
else()
	ExternalProject_Add(
		cstrace
		GIT_REPOSITORY https://github.com/damho1104/strace.git
		UPDATE_COMMAND "./bootstrap"
		BUILD_IN_SOURCE TRUE
		CONFIGURE_COMMAND "./configure" --enable-mpers=no --enable-stacktrace=no --program-prefix=c --prefix=${CMAKE_INSTALL_PREFIX}
		BUILD_COMMAND make
		INSTALL_DIR "${CMAKE_INSTALL_PREFIX}"
		INSTALL_COMMAND make install
	)
endif()