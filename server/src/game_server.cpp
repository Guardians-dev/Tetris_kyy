#include "game_server.hpp"
#include <iostream>
#include <cstring>
#include <unistd.h>
#include <string>

// GameState 구현
GameState::GameState() : board(BOARD_HEIGHT, std::vector<int>(BOARD_WIDTH, 0)) {}

bool GameState::isValidMove(const TetrisPiece& piece, int x, int y) const {
    for (size_t i = 0; i < piece.shape.size(); ++i) {
        for (size_t j = 0; j < piece.shape[i].size(); ++j) {
            if (piece.shape[i][j]) {
                int new_x = x + j;
                int new_y = y + i;
                if (new_x < 0 || new_x >= BOARD_WIDTH || 
                    new_y < 0 || new_y >= BOARD_HEIGHT ||
                    board[new_y][new_x]) {
                    return false;
                }
            }
        }
    }
    return true;
}

bool GameState::isValidRotation(const TetrisPiece& piece, int rotation) const {
    // 회전된 피스의 모양 계산
    std::vector<std::vector<int>> rotated = piece.shape;
    for (int r = 0; r < rotation % 4; ++r) {
        std::vector<std::vector<int>> temp(rotated[0].size(), 
                                         std::vector<int>(rotated.size()));
        for (size_t i = 0; i < rotated.size(); ++i) {
            for (size_t j = 0; j < rotated[i].size(); ++j) {
                temp[j][rotated.size() - 1 - i] = rotated[i][j];
            }
        }
        rotated = temp;
    }
    
    TetrisPiece rotated_piece = piece;
    rotated_piece.shape = rotated;
    return isValidMove(rotated_piece, piece.x, piece.y);
}

// Player 구현
Player::Player(int id, const sockaddr_in& addr) : id(id), address(addr) {}

// GameRoom 구현
GameRoom::GameRoom() {}

bool GameRoom::addPlayer(std::shared_ptr<Player> player) {
    std::lock_guard<std::mutex> lock(mutex);
    if (players.size() >= MAX_PLAYERS) {
        return false;
    }
    players[player->getId()] = player;
    return true;
}

bool GameRoom::removePlayer(int player_id) {
    std::lock_guard<std::mutex> lock(mutex);
    return players.erase(player_id) > 0;
}

bool GameRoom::isFull() const {
    return players.size() >= MAX_PLAYERS;
}

bool GameRoom::isEmpty() const {
    return players.empty();
}

void GameRoom::broadcastPacket(const Packet& packet, const sockaddr_in& sender, int sock) {
    std::lock_guard<std::mutex> lock(mutex);
    for (const auto& [id, player] : players) {
        if (memcmp(&player->getAddress(), &sender, sizeof(sockaddr_in)) != 0) {
            sendto(sock, packet.buffer, sizeof(Packet), 0,
                   (struct sockaddr*)&player->getAddress(), sizeof(sockaddr_in));
        }
    }
}

std::vector<std::shared_ptr<Player>> GameRoom::getPlayers() const {
    std::lock_guard<std::mutex> lock(mutex);
    std::vector<std::shared_ptr<Player>> result;
    for (const auto& [id, player] : players) {
        result.push_back(player);
    }
    return result;
}

bool GameRoom::validateMove(int player_id, const Packet& packet) const {
    std::lock_guard<std::mutex> lock(mutex);
    auto it = players.find(player_id);
    if (it == players.end()) {
        return false;
    }

    GameState& state = it->second->getGameState();
    TetrisPiece piece;
    piece.type = packet.header.data.move_data.piece_type;
    piece.x = packet.header.data.move_data.x;
    piece.y = packet.header.data.move_data.y;
    
    switch (static_cast<PacketType>(packet.header.type)) {
        case PacketType::MOVE_PIECE:
            return state.isValidMove(piece, piece.x, piece.y);
        case PacketType::ROTATE_PIECE:
            return state.isValidRotation(piece, packet.header.data.move_data.rotation);
        case PacketType::DROP_PIECE:
            return state.isValidMove(piece, piece.x, piece.y);
        default:
            return false;
    }
}

// GameServer 구현
GameServer::GameServer(int port) 
    : thread_pool(4)  // 4개의 작업자 스레드
    , next_player_id(1)
    , running(true)
{
    // UDP 소켓 생성
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        throw std::runtime_error("소켓 생성 실패");
    }

    // 소켓 timeout 설정 (1초)
    struct timeval tv;
    tv.tv_sec = 1;  // 1초
    tv.tv_usec = 0;
    if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv)) < 0) {
        close(sock);
        throw std::runtime_error("소켓 timeout 설정 실패");
    }

    // 서버 주소 설정
    sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    server_addr.sin_port = htons(port);

    // 소켓 바인딩
    if (bind(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        close(sock);
        throw std::runtime_error("소켓 바인딩 실패");
    }

    game_room = std::make_unique<GameRoom>();
    std::cout << "게임 서버가 포트 " << port << "에서 시작되었습니다." << std::endl;
    std::cout << "서버를 종료하려면 'exit'를 입력하세요." << std::endl;

    // 입력 처리 스레드 시작
    input_thread = std::make_unique<std::thread>(&GameServer::handleUserInput, this);
}

GameServer::~GameServer() {
    shutdown();
}

void GameServer::shutdown() {
    if (!running.exchange(false)) {
        return;  // Already shutting down
    }
    
    std::cout << "\nServer shutting down..." << std::endl;
    
    // Send disconnect packet to all players
    Packet disconnect_packet;
    disconnect_packet.header.type = PacketType::DISCONNECT;
    
    {
        std::lock_guard<std::mutex> lock(mutex);
        auto players = game_room->getPlayers();
        std::cout << "Notifying " << players.size() << " connected players..." << std::endl;
        
        for (const auto& player : players) {
            sendto(sock, disconnect_packet.buffer, sizeof(Packet), 0,
                   (struct sockaddr*)&player->getAddress(), sizeof(sockaddr_in));
            std::cout << "Sent disconnect notification to Player " << player->getId() << std::endl;
        }
    }
    
    if (sock >= 0) {
        close(sock);
        sock = -1;
    }
    
    std::cout << "Server shutdown complete." << std::endl;
}

void GameServer::handleUserInput() {
    std::string input;
    while (running) {
        std::getline(std::cin, input);
        if (input == "exit") {
            std::cout << "서버 종료를 시작합니다..." << std::endl;
            shutdown();
            break;
        }
    }
}

void GameServer::run() {
    Packet packet;
    sockaddr_in client_addr;
    socklen_t client_len = sizeof(client_addr);

    while (running) {
        ssize_t recv_len = recvfrom(sock, packet.buffer, sizeof(Packet), 0,
                                  (struct sockaddr*)&client_addr, &client_len);
        
        if (recv_len < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                // timeout 발생, running 플래그 확인하고 계속 진행
                continue;
            }
            std::cerr << "패킷 수신 실패: " << strerror(errno) << std::endl;
            continue;
        }

        // 패킷 처리를 스레드 풀에서 실행
        thread_pool.enqueue([this, packet, client_addr]() {
            handlePacket(packet, client_addr);
        });
    }
}

void GameServer::handlePacket(const Packet& packet, const sockaddr_in& client_addr) {
    switch (packet.header.type) {
        case PacketType::CONNECT_REQUEST: {
            std::lock_guard<std::mutex> lock(mutex);
            
            if (game_room->isFull()) {
                std::cout << "Connection rejected: Server is full (3/3 players)" << std::endl;
                return;
            }
            
            int player_id = assignPlayerId();
            auto player = std::make_shared<Player>(player_id, client_addr);
            
            if (game_room->addPlayer(player)) {
                // Send response packet
                Packet response;
                response.header.type = PacketType::CONNECT_RESPONSE;
                response.header.player_id = player_id;
                
                std::cout << "Player " << player_id << " connected from " 
                          << inet_ntoa(client_addr.sin_addr) << ":" << ntohs(client_addr.sin_port) 
                          << " (" << game_room->getPlayers().size() << "/3 players)" << std::endl;
                
                sendto(sock, response.buffer, sizeof(Packet), 0,
                       (struct sockaddr*)&client_addr, sizeof(client_addr));
                
                // If room is full after adding the player, start the game
                if (game_room->isFull()) {
                    std::cout << "All players connected. Starting the game..." << std::endl;
                    startGame();
                }
            }
            break;
        }
        
        case PacketType::DISCONNECT: {
            std::lock_guard<std::mutex> lock(mutex);
            
            // Find the player ID from the address
            auto players = game_room->getPlayers();
            for (const auto& player : players) {
                if (memcmp(&player->getAddress(), &client_addr, sizeof(sockaddr_in)) == 0) {
                    int player_id = player->getId();
                    if (game_room->removePlayer(player_id)) {
                        std::cout << "Player " << player_id << " disconnected from "
                                  << inet_ntoa(client_addr.sin_addr) << ":" << ntohs(client_addr.sin_port)
                                  << " (" << game_room->getPlayers().size() << "/3 players remaining)" << std::endl;
                    }
                    break;
                }
            }
            break;
        }
        
        case PacketType::MOVE_PIECE:
        case PacketType::ROTATE_PIECE:
        case PacketType::DROP_PIECE: {
            if (validateAndProcessMove(packet.header.player_id, packet)) {
                broadcastToRoom(packet, client_addr);
            }
            break;
        }
        
        case PacketType::BOARD_UPDATE: {
            broadcastToRoom(packet, client_addr);
            break;
        }
    }
}

bool GameServer::validateAndProcessMove(int player_id, const Packet& packet) {
    return game_room->validateMove(player_id, packet);
}

void GameServer::broadcastToRoom(const Packet& packet, const sockaddr_in& sender) {
    game_room->broadcastPacket(packet, sender, sock);
}

int GameServer::assignPlayerId() {
    return next_player_id++; 
}

void GameServer::startGame() {
    Packet start_packet;
    start_packet.header.type = PacketType::GAME_START;
    
    std::cout << "Broadcasting game start to all players..." << std::endl;
    
    // Broadcast to all players using a dummy sender address
    sockaddr_in dummy_addr{};
    broadcastToRoom(start_packet, dummy_addr);
}