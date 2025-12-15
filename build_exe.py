#!/usr/bin/env python3
"""
Touch The Grass - Build Script
Advanced PyInstaller build script with comprehensive options and error handling.
"""

import os
import sys
import shutil
import argparse
import logging
from pathlib import Path
from datetime import datetime
import PyInstaller.__main__


class BuildConfig:
    """Configuration class for build settings."""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.main_dir = self.project_root / "Main"
        self.assets_dir = self.main_dir / "Assets"
        self.game_dir = self.main_dir / "game"
        self.main_script = self.game_dir / "__main__.py"
        self.icon_path = self.assets_dir / "images" / "icon.ico"
        self.build_dir = self.project_root / "build"
        self.logs_dir = self.build_dir / "logs"
        self.dist_dir = self.project_root / "dist"
        self.specs_dir = self.project_root / "specs"
        self.spec_file = self.specs_dir / "TouchTheGrass.spec"

    def validate_paths(self):
        """Validate that all required paths exist."""
        required_paths = [
            self.main_dir,
            self.assets_dir,
            self.game_dir,
            self.main_script,
        ]

        missing_paths = []
        for path in required_paths:
            if not path.exists():
                missing_paths.append(str(path))

        if missing_paths:
            raise FileNotFoundError(f"Required paths not found: {', '.join(missing_paths)}")

        # Check for icon (optional but recommended)
        if not self.icon_path.exists():
            print(f"Warning: Icon file not found at {self.icon_path}. Build will continue without icon.")

        return True


class BuildTool:
    """Main build tool class."""

    def __init__(self):
        self.config = BuildConfig()
        self.prepare_directories()
        self.colors = self.init_colors()
        self.setup_logging()

    def prepare_directories(self):
        """Ensure required directories exist."""
        self.config.build_dir.mkdir(parents=True, exist_ok=True)
        self.config.logs_dir.mkdir(parents=True, exist_ok=True)
        self.config.specs_dir.mkdir(parents=True, exist_ok=True)

    def init_colors(self):
        """Return a dict of ANSI color codes (with Windows compatibility)."""
        if os.name == "nt":
            os.system("")
        return {
            "reset": "\033[0m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
        }

    def setup_logging(self):
        """Setup logging configuration."""
        # Ensure logs directory exists
        log_filename = self.config.logs_dir / f"build_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding="utf-8"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def cleanup_old_builds(self):
        """Clean up previous build artifacts."""
        self.logger.info("Cleaning up old build artifacts...")

        # Remove build directory
        if self.config.build_dir.exists():
            shutil.rmtree(self.config.build_dir)
            self.logger.info(f"Removed {self.config.build_dir}")

        # Remove dist directory
        if self.config.dist_dir.exists():
            shutil.rmtree(self.config.dist_dir)
            self.logger.info(f"Removed {self.config.dist_dir}")

        # Remove specs directory if it exists
        if self.config.specs_dir.exists():
            shutil.rmtree(self.config.specs_dir)
            self.logger.info(f"Removed {self.config.specs_dir}")

        # Recreate dirs
        self.prepare_directories()

    def get_build_options(self, args, mode, version_tag):
        """Get build options from arguments for a specific mode."""
        name_suffix = "OneFile" if mode == "onefile" else "OneDir"
        exe_name = f"TouchTheGrass_{name_suffix}_{version_tag}"
        options = [
            str(self.config.main_script),
            f"--name={exe_name}",
            "--noconsole",  # No console window
            "--noconfirm",  # Skip confirmation for faster builds
            f"--specpath={self.config.specs_dir}",
            f"--workpath={self.config.build_dir}",
        ]

        # Build mode
        if mode == "onefile":
            options.append("--onefile")
        else:
            options.append("--onedir")

        # Add data directories
        if self.config.assets_dir.exists():
            options.append(f"--add-data={self.config.assets_dir}{os.pathsep}Assets")
        if self.config.game_dir.exists():
            options.append(f"--add-data={self.config.game_dir}{os.pathsep}game")

        # Hidden imports
        options.extend([
            "--hidden-import=game",
            "--hidden-import=pygame",
            "--hidden-import=pygame.mixer",
        ])

        # Icon
        if self.config.icon_path.exists():
            options.append(f"--icon={self.config.icon_path}")

        if args.upx:
            options.append("--upx-dir=")  # Use system UPX if available

        if args.clean:
            options.append("--clean")

        if args.debug:
            options.remove("--noconsole")  # Show console for debugging
            options.append("--debug=all")

        return options

    def build(self, args):
        """Execute the build process."""
        try:
            self.logger.info("=== Touch The Grass Build Script ===")
            self.logger.info(f"Build mode: {args.mode}")
            self.logger.info(f"Project root: {self.config.project_root}")

            # Validate paths
            self.config.validate_paths()
            self.logger.info("Path validation successful")

            # Cleanup if requested
            if args.cleanup:
                self.cleanup_old_builds()

            version_tag = args.version.strip() if args.version else self.prompt_version()

            modes_to_build = ["onefile", "onedir"] if args.mode == "both" else [args.mode]

            for mode in modes_to_build:
                # Get build options
                build_options = self.get_build_options(args, mode, version_tag)
                self.logger.info(f"Build options for {mode}: {' '.join(build_options)}")

                # Execute PyInstaller
                self.logger.info(f"Starting PyInstaller build for {mode}...")
                start_time = datetime.now()

                PyInstaller.__main__.run(build_options)

                end_time = datetime.now()
                duration = end_time - start_time

                self.logger.info(f"Build completed successfully in {duration} for {mode}")
                self.show_build_results(mode, version_tag)

        except Exception as e:
            self.logger.error(f"Build failed: {str(e)}")
            sys.exit(1)

    def show_build_results(self, mode, version_tag):
        """Show build results and file locations."""
        name_suffix = "OneFile" if mode == "onefile" else "OneDir"
        exe_name = f"TouchTheGrass_{name_suffix}_{version_tag}"
        if mode == "onefile":
            exe_pattern = exe_name + (".exe" if os.name == 'nt' else "")
            exe_path = self.config.dist_dir / exe_pattern
            if exe_path.exists():
                size = exe_path.stat().st_size / (1024 * 1024)  # Size in MB
                self.logger.info(f"✓ Executable created: {exe_path} ({size:.2f} MB)")
        else:
            dist_path = self.config.dist_dir / exe_name
            exe_path = dist_path / (exe_name + (".exe" if os.name == "nt" else ""))
            if dist_path.exists():
                self.logger.info(f"✓ Distribution folder created: {dist_path}")
            if exe_path.exists():
                size = exe_path.stat().st_size / (1024 * 1024)  # Size in MB
                self.logger.info(f"✓ Executable created inside folder: {exe_path} ({size:.2f} MB)")

    def interactive_menu(self):
        """Show interactive menu for build options."""
        c = self.colors
        print("\n" + c["cyan"] + "=" * 54 + c["reset"])
        print(c["green"] + "   Touch The Grass - Build Aracı" + c["reset"])
        print(c["cyan"] + "=" * 54 + c["reset"])
        print(f"{c['yellow']}1){c['reset']} OneFile         - Tek .exe (önerilen)")
        print(f"{c['yellow']}2){c['reset']} OneDir          - Klasör çıktısı")
        print(f"{c['yellow']}3){c['reset']} Both            - OneFile + OneDir (aynı anda)")
        print(f"{c['yellow']}4){c['reset']} OneFile (UPX)   - Daha küçük boyut (UPX kurulu olmalı)")
        print(f"{c['yellow']}5){c['reset']} Debug           - OneFile + konsol çıkışı")
        print(f"{c['yellow']}6){c['reset']} Temiz + OneFile - Önce temizle sonra build")
        print(c["cyan"] + "-" * 54 + c["reset"])
        print(c["magenta"] + "Komut satırı örnekleri:" + c["reset"])
        print(c["blue"] + "  python build_exe.py --mode both --version 2.2.3" + c["reset"])
        print(c["blue"] + "  python build_exe.py --mode onefile --upx --version 2.2.3" + c["reset"])
        print(c["cyan"] + "=" * 54 + c["reset"])

        while True:
            try:
                choice = input("\nSeçiminizi girin (1-6): ").strip()

                if choice == "1":
                    return self.create_args(mode="onefile")
                elif choice == "2":
                    return self.create_args(mode="onedir")
                elif choice == "3":
                    return self.create_args(mode="both")
                elif choice == "4":
                    return self.create_args(mode="onefile", upx=True)
                elif choice == "5":
                    return self.create_args(mode="onefile", debug=True)
                elif choice == "6":
                    return self.create_args(mode="onefile", cleanup=True)
                else:
                    print("Geçersiz seçim! Lütfen 1-6 arasında bir sayı girin.")
            except KeyboardInterrupt:
                print("\nİptal edildi.")
                sys.exit(0)

    def create_args(self, mode="onefile", upx=False, debug=False, cleanup=False, version=None):
        """Create argument namespace for build."""
        args = argparse.Namespace()
        args.mode = mode
        args.upx = upx
        args.debug = debug
        args.cleanup = cleanup
        args.clean = cleanup
        args.version = version
        return args

    def prompt_version(self):
        """Prompt user for version string."""
        while True:
            version = input("Versiyon numarası (örn. 2.2.3): ").strip()
            if version:
                return version
            print("Lütfen boş bırakmayın.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Touch The Grass Build Tool")
    parser.add_argument(
        "--mode",
        choices=["onefile", "onedir", "both"],
        default="onefile",
        help="Build mode (default: onefile, 'both' runs onefile+onedir)"
    )
    parser.add_argument(
        "--upx",
        action="store_true",
        help="Enable UPX compression"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Create debug build with console"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean previous build artifacts"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean PyInstaller cache"
    )
    parser.add_argument(
        "--version",
        help="Version string to append to output names (e.g., 2.2.3)"
    )

    # Parse known args first to handle interactive mode
    args, unknown = parser.parse_known_args()

    # If no arguments provided, show interactive menu
    if len(sys.argv) == 1:
        builder = BuildTool()
        args = builder.interactive_menu()
    else:
        builder = BuildTool()

    builder.build(args)


if __name__ == "__main__":
    main()
