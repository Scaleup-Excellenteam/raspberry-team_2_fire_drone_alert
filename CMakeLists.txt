cmake_minimum_required(VERSION 3.5.0)
project(drone-fire)
find_package(OpenCV REQUIRED)
find_package(CURL REQUIRED)
add_executable(drone-fire main.cpp)
include_directories(${CURL_INCLUDE_DIR})
target_link_libraries(drone-fire ${OpenCV_LIBS} ${CURL_LIBRARIES} nlohmann_json)
FILE(COPY alarm-sound.mp3 DESTINATION "${CMAKE_BINARY_DIR}")
 
