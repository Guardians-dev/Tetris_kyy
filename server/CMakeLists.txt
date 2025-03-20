cmake_minimum_required(VERSION 3.10)
project(TetrisServer)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 소스 파일 추가
add_executable(tetris_server
    src/main.cpp
    src/game_server.cpp
    src/thread_pool.cpp
)

# 헤더 파일 경로 추가
target_include_directories(tetris_server PRIVATE
    ${CMAKE_SOURCE_DIR}/src
)

# 스레드 라이브러리 링크
target_link_libraries(tetris_server PRIVATE
    pthread
) 