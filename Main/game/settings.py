import os

# Determine the project root (one directory above the 'game' folder)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Screen settings
SCREEN_SIZE = (800, 600)
CENTER = (SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2)

# Directories for assets
IMAGES_DIR = os.path.join(PROJECT_ROOT, "Main")  # Assuming images are stored in the Main folder
FONTS_DIR = os.path.join(PROJECT_ROOT, "fonts")

# Asset file paths
CUSTOM_FONT_PATH = os.path.join(FONTS_DIR, "PixelifySans-Regular.ttf")
GRASS1_IMG_PATH = os.path.join(IMAGES_DIR, "grass1.png")

# Scale limits
MIN_SCALE = 0.9
MAX_SCALE = 1.2
