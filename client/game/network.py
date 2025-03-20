import socket
import struct
import threading
import json
import numpy as np
import os
from enum import IntEnum

class PacketType(IntEnum):
    CONNECT_REQUEST = 1
    CONNECT_RESPONSE = 2
    GAME_START = 3
    BOARD_UPDATE = 4
    DISCONNECT = 5
    MOVE_PIECE = 6
    ROTATE_PIECE = 7
    DROP_PIECE = 8

class Packet:
    HEADER_SIZE = 8  # type(4) + player_id(4)
    MOVE_DATA_SIZE = 16  # piece_type(4) + x(4) + y(4) + rotation(4)
    BOARD_DATA_SIZE = 1000
    TOTAL_SIZE = 1024

    def __init__(self):
        self.type = 0
        self.player_id = 0
        self.move_data = {'piece_type': 0, 'x': 0, 'y': 0, 'rotation': 0}
        self.board_data = bytearray(self.BOARD_DATA_SIZE)

    def pack(self):
        buffer = bytearray(self.TOTAL_SIZE)
        
        # 헤더 패킹
        struct.pack_into('=II', buffer, 0, self.type, self.player_id)
        
        # 데이터 패킹
        if self.type in [PacketType.MOVE_PIECE, PacketType.ROTATE_PIECE, PacketType.DROP_PIECE]:
            struct.pack_into('=iiii', buffer, self.HEADER_SIZE,
                           self.move_data['piece_type'],
                           self.move_data['x'],
                           self.move_data['y'],
                           self.move_data['rotation'])
        elif self.type == PacketType.BOARD_UPDATE:
            buffer[self.HEADER_SIZE:self.HEADER_SIZE + len(self.board_data)] = self.board_data
            
        return buffer

    def unpack(self, buffer):
        # 헤더 언패킹
        self.type, self.player_id = struct.unpack('=II', buffer[:self.HEADER_SIZE])
        
        # 데이터 언패킹
        if self.type in [PacketType.MOVE_PIECE, PacketType.ROTATE_PIECE, PacketType.DROP_PIECE]:
            move_data = struct.unpack('=iiii', buffer[self.HEADER_SIZE:self.HEADER_SIZE + self.MOVE_DATA_SIZE])
            self.move_data = {
                'piece_type': move_data[0],
                'x': move_data[1],
                'y': move_data[2],
                'rotation': move_data[3]
            }
        elif self.type == PacketType.BOARD_UPDATE:
            self.board_data = buffer[self.HEADER_SIZE:self.HEADER_SIZE + self.BOARD_DATA_SIZE]

class NetworkManager:
    def __init__(self, client_id='client1'):
        self.client_id = client_id
        self.config = self._load_config()
        self.host = self.config[client_id]['host']
        self.port = self.config[client_id]['port']
        self.client_port = self.config[client_id]['client_port']
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', self.client_port))  # 클라이언트별 고유 포트 바인딩
        
        self.connected = False
        self.opponent_boards = [None, None]
        self.player_id = None
        self.receive_thread = None
        self.game_started = False
        self.server_disconnected = False

    def _load_config(self):
        """Method to load configuration file"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load config file: {e}")
            return {
                "client1": {"host": "127.0.0.1", "port": 12345, "client_port": 50001},
                "client2": {"host": "127.0.0.1", "port": 12345, "client_port": 50002},
                "client3": {"host": "127.0.0.1", "port": 12345, "client_port": 50003}
            }

    def connect(self):
        try:
            # Set socket timeout (5 seconds)
            self.socket.settimeout(5.0)
            
            # Send connection request packet
            packet = Packet()
            packet.type = PacketType.CONNECT_REQUEST
            
            self.socket.sendto(packet.pack(), (self.host, self.port))
            
            # Wait for response
            buffer = bytearray(Packet.TOTAL_SIZE)
            self.socket.recv_into(buffer)
            
            # Remove timeout after successful connection (for receive loop)
            self.socket.settimeout(None)
            
            response = Packet()
            response.unpack(buffer)
            
            if response.type == PacketType.CONNECT_RESPONSE:
                self.player_id = response.player_id
                self.connected = True
                
                # Start receive thread
                self.receive_thread = threading.Thread(target=self._receive_loop)
                self.receive_thread.daemon = True
                self.receive_thread.start()
                
                return True
                
        except socket.timeout:
            print("Connection attempt timed out")
            return False
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        if self.connected:
            packet = Packet()
            packet.type = PacketType.DISCONNECT
            packet.player_id = self.player_id
            
            self.socket.sendto(packet.pack(), (self.host, self.port))
            self.connected = False
            self.socket.close()

    def send_move(self, piece_type, x, y, move_type=PacketType.MOVE_PIECE, rotation=0):
        if not self.connected:
            return
            
        packet = Packet()
        packet.type = move_type
        packet.player_id = self.player_id
        packet.move_data = {
            'piece_type': piece_type,
            'x': x,
            'y': y,
            'rotation': rotation
        }
        
        self.socket.sendto(packet.pack(), (self.host, self.port))

    def send_board_state(self, board):
        if not self.connected:
            return
            
        packet = Packet()
        packet.type = PacketType.BOARD_UPDATE
        packet.player_id = self.player_id
        
        # NumPy 배열을 바이트로 변환
        board_bytes = board.tobytes()
        packet.board_data[:len(board_bytes)] = board_bytes
        
        self.socket.sendto(packet.pack(), (self.host, self.port))

    def _receive_loop(self):
        buffer = bytearray(Packet.TOTAL_SIZE)
        
        while self.connected:
            try:
                self.socket.recv_into(buffer)
                packet = Packet()
                packet.unpack(buffer)
                
                if packet.type == PacketType.BOARD_UPDATE:
                    if packet.player_id != self.player_id:
                        # Update opponent's board state
                        board_array = np.frombuffer(packet.board_data, dtype=np.int32)
                        board_array = board_array.reshape((20, 10))  # Tetris board size
                        
                        if packet.player_id < self.player_id:
                            idx = packet.player_id - 1
                        else:
                            idx = packet.player_id - 2
                        self.opponent_boards[idx] = board_array
                
                elif packet.type == PacketType.GAME_START:
                    print("Game started!")
                    self.game_started = True

                elif packet.type == PacketType.DISCONNECT:
                    print("Server has shut down.")
                    self.server_disconnected = True
                    self.disconnect()
                    break
                    
            except Exception as e:
                print(f"Receive loop error: {e}")
                if not self.connected:
                    break

    def get_opponent_boards(self):
        return self.opponent_boards

    def is_game_started(self):
        return self.game_started

    def is_server_disconnected(self):
        return self.server_disconnected 