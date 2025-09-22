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
    try:
        # PyInstaller creates a temp    folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        print(f"Using _MEIPASS path: {base_path}")
    except Exception:
        # Get the directory containing the game package (Main directory)
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        print(f"Using fallback path: {base_path}")
    
    result = os.path.normpath(os.path.join(base_path, relative_path))
    print(f"Resolved path for {relative_path}: {result}")
    print(f"Path exists: {os.path.exists(result)}")
    print(f"Directory contents: {os.listdir(os.path.dirname(result))}")
    return result

#   def create_golden_grass(grass_img):
    """Creates a golden version of the grass image."""
    golden_img = grass_img.copy()
    
    # Altın renk değerleri
    gold_color = (255, 215, 0)  # RGB for gold
    
    # Piksel piksel işleme
    for x in range(golden_img.get_width()):
        for y in range(golden_img.get_height()):
            color = golden_img.get_at((x, y))
            if color.a != 0:  # Sadece görünür pikselleri işle
                # Yeşil değerleri altın tonlarına dönüştür
                green_value = color.g
                new_color = pygame.Color(
                    min(255, int(green_value * 1.2)),  # Kırmızı bileşeni artır
                    min(255, int(green_value * 0.9)),  # Yeşil bileşeni biraz azalt
                    min(255, int(green_value * 0.3))   # Mavi bileşeni azalt
                )
                golden_img.set_at((x, y), new_color)
    
    return golden_img

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
    
    # Altın çim versiyonunu oluştur
    # assets['golden_grass_img'] = create_golden_grass(grass_img)
    
    # Load custom font
    assets['custom_font'] = pygame.font.Font(resource_path(CUSTOM_FONT_PATH), 36)
    
    # Load icon image
    icon_img = pygame.image.load(resource_path(ICON_PATH)).convert_alpha()
    assets['icon'] = icon_img
    
    return assets
