from os.path import abspath , join , sep
import sys

def findFile(relative_path : str):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # skipcq: PYL-W0212
        base_path = sys._MEIPASS
    except Exception:
        base_path = abspath(".")

    return join(base_path, relative_path.replace("/", sep))