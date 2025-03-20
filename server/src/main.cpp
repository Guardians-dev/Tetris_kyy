#include "game_server.hpp"
#include <iostream>
#include <csignal>

volatile sig_atomic_t running = true;

void signal_handler(int signal) {
    running = false;
}

int main() {
    try {
        // SIGINT (Ctrl+C) 핸들러 설정
        std::signal(SIGINT, signal_handler);
        
        // 게임 서버 시작 (포트 12345 사용)
        GameServer server(12345);
        server.run();
    }
    catch (const std::exception& e) {
        std::cerr << "예외 발생: " << e.what() << std::endl;
        return 1;
    }

    return 0;
} 