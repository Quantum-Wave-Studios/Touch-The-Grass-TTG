import os
import PyInstaller.__main__

main_dir = os.path.join(os.path.dirname(__file__), "Main")
assets_dir = os.path.join(main_dir, "Assets")
game_dir = os.path.join(main_dir, "game")


def build_exe():
    print("Pygame projenizi .exe'ye dönüştürmek için bir seçenek seçin:")
    print("1 - Tek dosya (onefile)")
    print("2 - Klasör (onedir)")
    choice = input("Seçiminizi girin (1 veya 2): ")

    if choice == "1":
        onefile = True
    elif choice == "2":
        onefile = False
    else:
        print("Geçersiz seçim! Lütfen 1 veya 2 girin.")
        return

    PyInstaller.__main__.run(
        [
            os.path.join(game_dir, "__main__.py"),
            "--name=TouchTheGrass",
            "--noconsole",
            "--onefile" if onefile else "--onedir",
            f"--add-data={assets_dir}{os.pathsep}Assets",
            f"--add-data={game_dir}{os.pathsep}game",
            "--hidden-import=game",
            "--icon=Main/Assets/images/icon.ico",
        ]
    )


if __name__ == "__main__":
    build_exe()
