import pygame
import os
from .settings import GRASS1_IMG_PATH, CUSTOM_FONT_PATH


def load_assets():
    """Yüklenmiş olan görselleri ve fontları döndürür."""
    assets = {}
    
    # grass1 resmini yükle ve ölçekle
    grass_img = pygame.image.load(GRASS1_IMG_PATH).convert_alpha()
    original_width = grass_img.get_width()
    original_height = grass_img.get_height()
    grass_img = pygame.transform.scale(grass_img, (int(original_width / 2.4), int(original_height / 2.4)))
    assets['grass_img'] = grass_img
    
    # Özel fontu yükle
    assets['custom_font'] = pygame.font.Font(CUSTOM_FONT_PATH, 36)
    
    return assets
