if __name__ == '__main__' and __package__ is None:
    import os, sys
    # Add the parent directory to sys.path so that the package can be found
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    __package__ = "game"

from .game import run_game

if __name__ == '__main__':
    run_game()
