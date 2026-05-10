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

add_executable(test_toyota_prius_2010_pt
    ${CMAKE_CURRENT_LIST_DIR}/../components/vehicle_comms/toyota_prius_2010_pt.c
    ${CMAKE_CURRENT_LIST_DIR}/test_toyota_prius_2010_pt.c
)

target_include_directories(test_toyota_prius_2010_pt PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}/../components/vehicle_comms
)

target_link_libraries(test_toyota_prius_2010_pt PRIVATE unity m)

add_test(NAME test_toyota_prius_2010_pt COMMAND test_toyota_prius_2010_pt)
