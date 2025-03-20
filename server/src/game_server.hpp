#pragma once

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <memory>
#include <map>
#include <vector>
#include <mutex>
#include <thread>
#include <atomic>
#include "thread_pool.hpp"

// 패킷 타입 정의
enum class PacketType : uint32_t {
    CONNECT_REQUEST = 1,
    CONNECT_RESPONSE = 2,
    GAME_START = 3,
    BOARD_UPDATE = 4,
    DISCONNECT = 5,
    MOVE_PIECE = 6,
    ROTATE_PIECE = 7,
    DROP_PIECE = 8
};

// 게임 검증을 위한 테트리스 피스 정의
struct TetrisPiece {
    std::vector<std::vector<int>> shape;
    int x, y;
    int type;
};

// 패킷 구조체 정의
union Packet {
    struct {
        PacketType type;      // PacketType으로 변경
        uint32_t player_id; // 플레이어 ID
        union {
            struct {
                int piece_type;
                int x;
                int y;
                int rotation;
            } move_data;
            uint8_t board_data[1000];
        } data;
    } header;
    uint8_t buffer[1024];
};

// 게임 상태를 저장하는 클래스
class GameState {
public:
    static const int BOARD_WIDTH = 10;
    static const int BOARD_HEIGHT = 20;
    
    GameState();
    bool isValidMove(const TetrisPiece& piece, int x, int y) const;
    bool isValidRotation(const TetrisPiece& piece, int rotation) const;
    void applyMove(const TetrisPiece& piece);
    void clearLines();
    
private:
    std::vector<std::vector<int>> board;
};

// 플레이어 정보를 저장하는 클래스
class Player {
public:
    Player(int id, const sockaddr_in& addr);
    int getId() const { return id; }
    const sockaddr_in& getAddress() const { return address; }
    GameState& getGameState() { return game_state; }

private:
    int id;
    sockaddr_in address;
    GameState game_state;
};

// 게임 방 클래스
class GameRoom {
public:
    GameRoom();
    bool addPlayer(std::shared_ptr<Player> player);
    bool removePlayer(int player_id);
    bool isFull() const;
    bool isEmpty() const;
    void broadcastPacket(const Packet& packet, const sockaddr_in& sender, int sock);
    std::vector<std::shared_ptr<Player>> getPlayers() const;
    bool validateMove(int player_id, const Packet& packet) const;

private:
    static const int MAX_PLAYERS = 3;
    std::map<int, std::shared_ptr<Player>> players;
    mutable std::mutex mutex;
};

// 게임 서버 클래스
class GameServer {
public:
    GameServer(int port);
    ~GameServer();
    void run();

private:
    void handlePacket(const Packet& packet, const sockaddr_in& sender);
    int assignPlayerId();
    void broadcastToRoom(const Packet& packet, const sockaddr_in& sender);
    bool validateAndProcessMove(int player_id, const Packet& packet);
    void handleUserInput();  // 사용자 입력 처리 함수
    void shutdown();         // 서버 종료 함수
    void startGame();        // 게임 시작 함수

    int sock;
    std::unique_ptr<GameRoom> game_room;
    ThreadPool thread_pool;
    int next_player_id;
    std::mutex mutex;
    std::atomic<bool> running;
    std::unique_ptr<std::thread> input_thread;
}; 