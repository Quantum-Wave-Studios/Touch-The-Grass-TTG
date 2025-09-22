import sys
import os

# PyInstaller ile çalışırken asset ve modül yolu
if hasattr(sys, '_MEIPASS'):
    os.chdir(sys._MEIPASS)

if __name__ == '__main__':
    import sys, os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    from game.game import run_game
    run_game()
