import pygame
import sys
from game.tetris import TetrisGame
from game.network import NetworkManager

# 상수 정의
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 50

# 색상 정의
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
RED = (255, 0, 0)

class MainMenu:
    def __init__(self, client_id='client1'):
        self.client_id = client_id
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(f"Tetris - {client_id}")
        self.clock = pygame.time.Clock()
        self.network = NetworkManager(client_id)
        self.show_error = False
        self.error_message = ""
        self.error_timer = 0
        
    def draw_button(self, text, x, y, width, height):
        button_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, GRAY, button_rect)
        font = pygame.font.Font(None, 36)
        text_surface = font.render(text, True, BLACK)
        text_rect = text_surface.get_rect(center=button_rect.center)
        self.screen.blit(text_surface, text_rect)
        return button_rect
        
    def show_error_message(self, message):
        self.show_error = True
        self.error_message = message
        self.error_timer = pygame.time.get_ticks()
        
    def draw_error_message(self):
        if self.show_error:
            # Display error message for 3 seconds
            if pygame.time.get_ticks() - self.error_timer > 3000:
                self.show_error = False
                return
                
            font = pygame.font.Font(None, 36)
            text_surface = font.render(self.error_message, True, RED)
            text_rect = text_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 100))
            self.screen.blit(text_surface, text_rect)

    def run(self):
        while True:
            self.screen.fill(WHITE)
            
            # Place button in center
            connect_button = self.draw_button(
                "Connect to Server",
                WINDOW_WIDTH // 2 - BUTTON_WIDTH // 2,
                WINDOW_HEIGHT // 2 - BUTTON_HEIGHT // 2,
                BUTTON_WIDTH,
                BUTTON_HEIGHT
            )
            
            # Display error message if any
            self.draw_error_message()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if connect_button.collidepoint(event.pos):
                        if self.network.connect():
                            game = TetrisGame(self.screen, self.network)
                            game.run()
                            self.network.disconnect()
                        else:
                            self.show_error_message("Failed to connect to server")

            pygame.display.flip()
            self.clock.tick(60)

def main():
    # Get client ID from command line arguments
    if len(sys.argv) != 2 or sys.argv[1] not in ['client1', 'client2', 'client3']:
        print("Usage: python main.py [client1|client2|client3]")
        sys.exit(1)
        
    client_id = sys.argv[1]
    menu = MainMenu(client_id)
    menu.run()

if __name__ == "__main__":
    main() 