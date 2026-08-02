"""Script de lancement simplifié pour WhatsApp Desktop Assistant."""

import sys
import os

# S'assurer que le répertoire courant est la racine du projet
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import main

if __name__ == "__main__":
    main()
