cmake_minimum_required (VERSION 3.0)
project(cbs)

IF(NOT CMAKE_BUILD_TYPE)
    SET(CMAKE_BUILD_TYPE "RELEASE")
ENDIF()

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++14")

include_directories("inc")
file(GLOB SOURCES "src/*.cpp")
add_executable(cbs ${SOURCES})

# Find Boost
SET(CMAKE_INCLUDE_PATH ${CMAKE_INCLUDE_PATH} "D:/boost_1_80_0")
SET(CMAKE_LIBRARY_PATH ${CMAKE_LIBRARY_PATH} "D:/boost_1_80_0/stage/lib")
set(Boost_USE_STATIC_LIBS        ON)  # only find static libs
find_package(Boost REQUIRED COMPONENTS program_options system filesystem)
include_directories( ${Boost_INCLUDE_DIRS} )
target_link_libraries(cbs ${Boost_LIBRARIES})

