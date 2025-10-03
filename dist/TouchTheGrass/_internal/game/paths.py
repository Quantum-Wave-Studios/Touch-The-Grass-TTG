# game/paths.py
import os

# Bu dosya, projenin ana klasörüne (Main) göre varlıkların göreceli yollarını tanımlar.
# assets.py dosyasındaki resource_path fonksiyonu, bu yolları çalışma zamanında mutlak yollara dönüştürecektir.

ASSETS_DIR = "assets"
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")

# Varlık dosyalarının yolları
CUSTOM_FONT_PATH = os.path.join(FONTS_DIR, "PixelifySans-Regular.ttf")
GRASS1_IMG_PATH = os.path.join(IMAGES_DIR, "grass1.png")
ICON_PATH = os.path.join(IMAGES_DIR, "icon.ico")
CLICK_SOUND_PATH = os.path.join(SOUNDS_DIR, "click.mp3")
BACK_SOUND_PATH = os.path.join(SOUNDS_DIR, "back.mp3")