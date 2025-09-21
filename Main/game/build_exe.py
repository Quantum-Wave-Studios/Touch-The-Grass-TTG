# Build script for Touch The Grass executable
import os
import sys
import shutil
import subprocess
from pathlib import Path

def get_project_paths():
    """Get all necessary project paths."""
    module_dir = Path(__file__).resolve().parent
    project_root = module_dir.parent.parent
    main_dir = project_root / "Main"
    
    return {
        "project_root": str(project_root),
        "main_dir": str(main_dir),
        "game_dir": str(main_dir / "game"),
        "dist_dir": str(project_root / "dist"),
        "build_dir": str(project_root / "build"),
        "assets_dir": str(main_dir / "assets"),
        "main_script": str(main_dir / "game" / "__main__.py"),
        "icon_path": str(main_dir / "assets" / "images" / "icon.png")
    }

def build_exe():
    """Build a single executable file for Touch The Grass."""
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    paths = get_project_paths()
    
    # Clean previous builds
    for dir_path in [paths["dist_dir"], paths["build_dir"]]:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
    
    # Set up environment
    os.environ["PYTHONPATH"] = os.pathsep.join([paths["main_dir"], os.environ.get("PYTHONPATH", "")])
    
    # Build command with debug options
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--onefile",
        "--name", "TouchTheGrass",
        "--clean",
        "--debug", "all",  # Enable all debug options
        "--icon", paths["icon_path"],
        "--add-data", f"{paths['assets_dir']};assets",  # Assets directly in root
        "--paths", paths["main_dir"],
        "--distpath", paths["dist_dir"],
        "--workpath", paths["build_dir"],
        "--exclude-module", "_bootlocale",  # Exclude problematic module
        "--log-level", "DEBUG"  # Show detailed debug info
    ]
    
    # Add all necessary imports
    imports = [
        "pygame", "pygame._sdl2",
        "game", "game.game", "game.game_loop",
        "game.settings", "game.assets", "game.paths"
    ]
    
    for module in imports:
        cmd.extend(["--hidden-import", module])
    
    # Add pygame submodules
    pygame_submodules = [
        "base", "bufferproxy", "color", "colordict",
        "cursors", "display", "draw", "event", "font",
        "freetype", "gfxdraw", "image", "imageext",
        "joystick", "key", "locals", "mask", "math",
        "mixer", "mixer_music", "mouse", "pixelarray",
        "pixelcopy", "rect", "rwobject", "scrap",
        "sndarray", "sprite", "surface", "surflock",
        "sysfont", "time", "transform", "_sdl2.audio",
        "_sdl2.video", "_sdl2.controller", "_sdl2.haptic"
    ]
    
    for submodule in pygame_submodules:
        cmd.extend(["--hidden-import", f"pygame.{submodule}"])
    
    # Add runtime hooks
    cmd.extend([
        "--runtime-hook",
        os.path.join(paths["game_dir"], "runtime_hook.py")
    ])
    
    # Add main script
    cmd.append(paths["main_script"])
    
    print("\nBuilding executable...")
    print("\nCommand:", " ".join(cmd))
    
    try:
        subprocess.run(cmd, check=True)
        print("\nBuild completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\nError during build: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_exe()
