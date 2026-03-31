"""Point d'entrée principal de l'application WhatsApp Desktop Assistant."""

import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ui.app_controller import AppController
from app.ui.main_window import MainWindow
from app.utils.logger import app_logger
from config.settings import AppSettings

logger = app_logger


def main():
    """Lance l'application."""
    logger.info("=" * 60)
    logger.info("Démarrage de WhatsApp Desktop Assistant")
    logger.info("=" * 60)

    # Charger la configuration
    settings = AppSettings()

    logger.info("Mode: %s", "SIMULATION" if settings.simulation_mode else "PRODUCTION")
    logger.info("Provider IA: %s", settings.ai_provider)
    logger.info("Mode réponse: %s", settings.response_mode)

    # Créer le contrôleur
    controller = AppController(settings)

    # Créer et lancer l'interface
    try:
        window = MainWindow(controller)
        # Charger les paramètres dans l'UI
        window.load_settings(controller.get_current_settings())
        logger.info("Interface utilisateur initialisée")

        # Lancer la boucle principale
        window.run()
    except ImportError as e:
        logger.error("Erreur d'import: %s", e)
        logger.error(
            "Assurez-vous d'avoir installé les dépendances: pip install -r requirements.txt"
        )
        sys.exit(1)
    except Exception as e:
        logger.error("Erreur fatale: %s", e)
        raise
    finally:
        logger.info("Application fermée")


if __name__ == "__main__":
    main()
