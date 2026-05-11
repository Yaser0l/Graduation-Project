cmake_minimum_required(VERSION 3.22)

project(MechanicUnitTests C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

option(ENABLE_COVERAGE "Enable coverage reporting" OFF)

include(FetchContent)
FetchContent_Declare(
    unity
    GIT_REPOSITORY https://github.com/ThrowTheSwitch/Unity.git
    GIT_TAG v2.6.0
)
FetchContent_MakeAvailable(unity)

if(NOT TARGET unity)
    add_library(unity STATIC ${unity_SOURCE_DIR}/src/unity.c)
    target_include_directories(unity PUBLIC ${unity_SOURCE_DIR}/src)
endif()

if(ENABLE_COVERAGE AND (CMAKE_C_COMPILER_ID MATCHES "GNU|Clang"))
    add_compile_options(-O0 -g --coverage)
    add_link_options(--coverage)
endif()

enable_testing()


add_executable(test_canmodule
    ${CMAKE_CURRENT_LIST_DIR}/test_canmodule.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/esp_twai_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/../components/vehicle_comms/toyota_prius_2010_pt.c
)

target_include_directories(test_canmodule PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}/../components/vehicle_comms
    ${CMAKE_CURRENT_LIST_DIR}/stubs
)

target_link_libraries(test_canmodule PRIVATE unity m)

add_test(NAME test_canmodule COMMAND test_canmodule)

add_executable(test_dtc_reporter
    ${CMAKE_CURRENT_LIST_DIR}/test_dtc_reporter.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/esp_isotp_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/esp_timer_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/local_mqtt_stubs.c
)

target_include_directories(test_dtc_reporter PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}/stubs
    ${CMAKE_CURRENT_LIST_DIR}/../components/vehicle_comms
)

target_link_libraries(test_dtc_reporter PRIVATE unity)

add_test(NAME test_dtc_reporter COMMAND test_dtc_reporter)

add_executable(test_local_mqtt
    ${CMAKE_CURRENT_LIST_DIR}/test_local_mqtt.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/esp_event_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/esp_timer_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/esp_random_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/mqtt_client_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/nvs_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/../components/network/network_events.c
)

target_include_directories(test_local_mqtt PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}/stubs
    ${CMAKE_CURRENT_LIST_DIR}/../components/network
    ${CMAKE_CURRENT_LIST_DIR}/../components/vehicle_comms
)

target_link_libraries(test_local_mqtt PRIVATE unity)

add_test(NAME test_local_mqtt COMMAND test_local_mqtt)

add_executable(test_wifi_store
    ${CMAKE_CURRENT_LIST_DIR}/test_wifi_store.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/nvs_stubs.c
)

target_include_directories(test_wifi_store PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}/stubs
    ${CMAKE_CURRENT_LIST_DIR}/../components/network
)

target_link_libraries(test_wifi_store PRIVATE unity)

add_test(NAME test_wifi_store COMMAND test_wifi_store)

add_executable(test_wifi_manager
    ${CMAKE_CURRENT_LIST_DIR}/test_wifi_manager.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/esp_event_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/esp_wifi_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/event_groups_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/gpio_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/stubs/nvs_stubs.c
    ${CMAKE_CURRENT_LIST_DIR}/../components/network/network_events.c
    ${CMAKE_CURRENT_LIST_DIR}/../components/network/wifi_store.c
)

target_include_directories(test_wifi_manager PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}/stubs
    ${CMAKE_CURRENT_LIST_DIR}/../components/network
)

target_link_libraries(test_wifi_manager PRIVATE unity)

add_test(NAME test_wifi_manager COMMAND test_wifi_manager)
