import pygame
import sys
import os
from . import settings, assets, game_loop


def run_game():
    # Initialize pygame
    pygame.init()
    pygame.mixer.init()
    # Set up the game window using settings
    screen = pygame.display.set_mode(settings.SCREEN_SIZE)
    clock = pygame.time.Clock()
    
    # Load assets (images, fonts, etc.)
    loaded_assets = assets.load_assets()
    
    # Set window caption and icon using loaded assets (if available)
    pygame.display.set_caption("Touch The Grass   (Bet you can't touch it IRL!)")
    if 'icon' in loaded_assets:
        pygame.display.set_icon(loaded_assets['icon'])
    
    # Start the main game loop
    game_loop.run_loop(screen, clock, loaded_assets)