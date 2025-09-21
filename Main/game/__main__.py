import sys
import os

# PyInstaller ile çalışırken asset ve modül yolu
if hasattr(sys, '_MEIPASS'):
    os.chdir(sys._MEIPASS)

if __name__ == '__main__' and __package__ is None:
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    __package__ = "game"
from .game import run_game

if __name__ == '__main__':
    run_game()
