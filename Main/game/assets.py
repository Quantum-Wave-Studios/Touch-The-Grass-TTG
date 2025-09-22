import pygame
import os
import sys
from .settings import SCREEN_SIZE
from .paths import (
    GRASS1_IMG_PATH,
    CUSTOM_FONT_PATH,
    ICON_PATH,
    CLICK_SOUND_PATH
)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        print(f"Using _MEIPASS path: {base_path}")
    else:
        # Get the directory containing the game package (Main directory)
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        print(f"Using development path: {base_path}")
    
    result = os.path.normpath(os.path.join(base_path, relative_path))
    
    if not os.path.exists(result):
        print(f"Warning: Resource not found at {result}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Directory contents: {os.listdir(os.path.dirname(result))}")
    else:
        print(f"Resource found: {result}")
    
    return result

def load_assets():
    """Loads and returns all the assets for the game."""
    assets = {}
    
    # Load and scale grass image
    path = resource_path(GRASS1_IMG_PATH)
    print(f"Attempting to load grass image from: {path}")
    print(f"File exists: {os.path.exists(path)}")
    grass_img = pygame.image.load(path).convert_alpha()
    original_width, original_height = grass_img.get_size()
    grass_img = pygame.transform.scale(grass_img, (int(original_width / 2.4), int(original_height / 2.4)))
    assets['grass_img'] = grass_img
    
    # Load custom font
    assets['custom_font'] = pygame.font.Font(resource_path(CUSTOM_FONT_PATH), 36)
    
    # Load icon image
    icon_img = pygame.image.load(resource_path(ICON_PATH)).convert_alpha()
    assets['icon'] = icon_img
    
    return assets
