file(GLOB TEST_SRCS "*.c")

if(TEST_SRCS)
	idf_component_register(
		SRCS ${TEST_SRCS}
		INCLUDE_DIRS "."
		PRIV_REQUIRES unity main
	)
endif()

