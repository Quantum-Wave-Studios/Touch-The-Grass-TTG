import pygame
import sys
from . import settings, assets, game_loop


def run_game():
    # Initialize pygame
    pygame.init()
    # Set up the game window using settings
    screen = pygame.display.set_mode(settings.SCREEN_SIZE)
    clock = pygame.time.Clock()
    
    # Load assets (images, fonts, etc.)
    loaded_assets = assets.load_assets()
    
    # Start the main game loop
    game_loop.run_loop(screen, clock, loaded_assets)
