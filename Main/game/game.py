import pygame
import sys
import os
from . import settings, assets, game_loop


def run_game():
    # Initialize pygame
    pygame.init()
    # Initialize audio safely. On some platforms (headless Linux, Wine) the
    # mixer backend can fail to initialize and raise. Try normal init first;
    # if it fails, try using the SDL dummy audio driver to allow the game to
    # run without sound. We expose a flag on game_loop to let the rest of the
    # code avoid audio operations when unavailable.
    try:
        pygame.mixer.init()
        game_loop.MIXER_AVAILABLE = True
    except Exception:
        # Try dummy driver fallback so code that imports mixer functions
        # won't crash. Set MIXER_AVAILABLE=False so callers can skip audio.
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        try:
            pygame.mixer.init()
            game_loop.MIXER_AVAILABLE = False
        except Exception:
            game_loop.MIXER_AVAILABLE = False
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