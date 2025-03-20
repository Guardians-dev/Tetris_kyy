import pygame
import random
import numpy as np

# 테트리스 블록 색상을 TETRIS BLOCK COLORS로 변경
COLORS = [
    (0, 0, 0),        # Empty space
    (255, 0, 0),      # I
    (0, 255, 0),      # J
    (0, 0, 255),      # L
    (255, 255, 0),    # O
    (255, 0, 255),    # S
    (0, 255, 255),    # T
    (128, 0, 128)     # Z
]

# 테트리미노 모양을 TETRIMINO SHAPES로 변경
SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[2, 0, 0],      # J
     [2, 2, 2]],
    [[0, 0, 3],      # L
     [3, 3, 3]],
    [[4, 4],         # O
     [4, 4]],
    [[0, 5, 5],      # S
     [5, 5, 0]],
    [[0, 6, 0],      # T
     [6, 6, 6]],
    [[7, 7, 0],      # Z
     [0, 7, 7]]
]

class TetrisGame:
    def __init__(self, screen, network, width=10, height=20):
        self.screen = screen
        self.network = network
        self.width = width
        self.height = height
        self.block_size = 30
        self.board = np.zeros((height, width), dtype=int)
        
        # 메인 게임 영역 크기 및 위치
        self.game_width = self.block_size * width
        self.game_height = self.block_size * height
        self.game_x = (screen.get_width() - self.game_width) // 2
        self.game_y = (screen.get_height() - self.game_height) // 2

        # 상대방 게임 영역 크기 및 위치 (축소된 크기)
        self.opponent_scale = 0.5
        self.opponent_width = int(self.game_width * self.opponent_scale)
        self.opponent_height = int(self.game_height * self.opponent_scale)
        
        # 현재 블록 초기화
        self.current_piece = None
        self.current_x = 0
        self.current_y = 0
        self.new_piece()

        # 게임 상태
        self.game_over = False
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        
        # 타이머 설정
        self.drop_time = 0
        self.drop_speed = 1000  # 초기 낙하 속도 (ms)
        self.last_drop = pygame.time.get_ticks()

    def new_piece(self):
        self.current_piece = random.choice(SHAPES)
        self.current_x = self.width // 2 - len(self.current_piece[0]) // 2
        self.current_y = 0
        
        if not self.is_valid_move(self.current_piece, self.current_x, self.current_y):
            self.game_over = True

    def rotate_piece(self):
        rotated = list(zip(*self.current_piece[::-1]))
        if self.is_valid_move(rotated, self.current_x, self.current_y):
            self.current_piece = rotated

    def is_valid_move(self, piece, x, y):
        for i, row in enumerate(piece):
            for j, cell in enumerate(row):
                if cell:
                    if (y + i >= self.height or
                        x + j < 0 or
                        x + j >= self.width or
                        y + i < 0 or
                        self.board[y + i][x + j]):
                        return False
        return True

    def merge_piece(self):
        for i, row in enumerate(self.current_piece):
            for j, cell in enumerate(row):
                if cell:
                    self.board[self.current_y + i][self.current_x + j] = cell
        self.clear_lines()
        self.new_piece()

    def clear_lines(self):
        lines = 0
        for i in range(self.height):
            if all(self.board[i]):
                self.board = np.vstack((np.zeros((1, self.width)), self.board[:i], self.board[i+1:]))
                lines += 1
        
        if lines > 0:
            self.lines_cleared += lines
            self.score += lines * 100 * self.level
            self.level = self.lines_cleared // 10 + 1
            self.drop_speed = max(100, 1000 - (self.level - 1) * 100)

    def draw_board(self, surface, x, y, width, height, board):
        block_width = width // self.width
        block_height = height // self.height
        
        for i in range(self.height):
            for j in range(self.width):
                pygame.draw.rect(surface, COLORS[board[i][j]],
                               (x + j * block_width,
                                y + i * block_height,
                                block_width - 1,
                                block_height - 1))

    def draw_current_piece(self, surface, x, y, block_width, block_height):
        if self.current_piece:
            for i, row in enumerate(self.current_piece):
                for j, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(surface, COLORS[cell],
                                       (x + (self.current_x + j) * block_width,
                                        y + (self.current_y + i) * block_height,
                                        block_width - 1,
                                        block_height - 1))

    def draw(self):
        # 메인 게임 영역 그리기
        self.draw_board(self.screen, self.game_x, self.game_y, 
                       self.game_width, self.game_height, self.board)
        self.draw_current_piece(self.screen, self.game_x, self.game_y,
                              self.block_size, self.block_size)

        # 상대방 게임 영역 그리기 (우측 상단, 하단)
        opponent_x = self.screen.get_width() - self.opponent_width - 20
        opponent_y1 = 20
        opponent_y2 = self.screen.get_height() - self.opponent_height - 20
        
        pygame.draw.rect(self.screen, (128, 128, 128),
                        (opponent_x, opponent_y1,
                         self.opponent_width, self.opponent_height))
        pygame.draw.rect(self.screen, (128, 128, 128),
                        (opponent_x, opponent_y2,
                         self.opponent_width, self.opponent_height))

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    if self.is_valid_move(self.current_piece,
                                        self.current_x - 1,
                                        self.current_y):
                        self.current_x -= 1
                elif event.key == pygame.K_RIGHT:
                    if self.is_valid_move(self.current_piece,
                                        self.current_x + 1,
                                        self.current_y):
                        self.current_x += 1
                elif event.key == pygame.K_DOWN:
                    if self.is_valid_move(self.current_piece,
                                        self.current_x,
                                        self.current_y + 1):
                        self.current_y += 1
                elif event.key == pygame.K_UP:
                    self.rotate_piece()
                elif event.key == pygame.K_SPACE:
                    while self.is_valid_move(self.current_piece,
                                           self.current_x,
                                           self.current_y + 1):
                        self.current_y += 1
                    self.merge_piece()
        return True

    def update(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_drop > self.drop_speed:
            if self.is_valid_move(self.current_piece,
                                self.current_x,
                                self.current_y + 1):
                self.current_y += 1
            else:
                self.merge_piece()
            self.last_drop = current_time

    def run(self):
        clock = pygame.time.Clock()
        
        # Wait for game to start
        while not self.network.is_game_started():
            if self.network.is_server_disconnected():
                self.show_message("Server has shut down")
                return

            self.screen.fill((0, 0, 0))
            self.show_message("Waiting for other players...")
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.network.disconnect()
                    return
                    
            pygame.display.flip()
            clock.tick(60)

        while not self.game_over:
            if self.network.is_server_disconnected():
                self.show_message("Server has shut down")
                return

            if not self.handle_input():
                self.network.disconnect()
                break
            
            self.update()
            self.screen.fill((0, 0, 0))
            self.draw()
            pygame.display.flip()
            clock.tick(60)

        # Game over handling
        self.show_message("Game Over")
        pygame.time.wait(2000)

    def show_message(self, text):
        """Helper method to display a message in the center of the screen"""
        self.screen.fill((0, 0, 0))
        font = pygame.font.Font(None, 48)
        text_surface = font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.screen.get_width() // 2,
                                                 self.screen.get_height() // 2))
        self.screen.blit(text_surface, text_rect)
        pygame.display.flip() 