set(srcs)
set(include_dirs "include")
set(requires)
set(priv_requires)

# Both backends are listed unconditionally so that their Kconfig menus are
# always loaded (MINIMAL_BUILD would otherwise exclude them before Kconfig
# is parsed, making their symbols "unknown" — a chicken-and-egg problem).
list(APPEND priv_requires "wifi_manager" "ethernet_qemu")

list(APPEND srcs "network_wrapper.c")

idf_component_register(
    SRCS "${srcs}"
    INCLUDE_DIRS "${include_dirs}"
    REQUIRES
        "${requires}"
    PRIV_REQUIRES
        "${priv_requires}"
)