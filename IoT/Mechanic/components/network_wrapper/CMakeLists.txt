set(srcs)
set(include_dirs "include")

list(APPEND srcs "network_wrapper.c" "network_events.c")
idf_component_register(
    SRCS "${srcs}"
    INCLUDE_DIRS "${include_dirs}"
)