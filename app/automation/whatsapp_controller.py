"""Module d'automatisation WhatsApp Desktop via UI Automation (pywinauto).

Ce module isole toute la logique d'interaction avec l'interface Windows de WhatsApp Desktop.
Il utilise pywinauto pour détecter la fenêtre, lire les messages et envoyer des réponses.

ATTENTION: L'automatisation UI est intrinsèquement fragile. Les sélecteurs peuvent
changer lors des mises à jour de WhatsApp. Ce module documente les points de fragilité
et propose des alternatives quand possible.

Architecture WhatsApp Desktop (Windows, UWP/Electron):
- La fenêtre principale contient une liste de conversations à gauche
- Le panneau de droite contient les messages de la conversation active
- Les messages non lus sont marqués par un badge sur la conversation
- Le champ de saisie est en bas du panneau de droite
"""

import time
from dataclasses import dataclass
from typing import Optional

from app.utils.logger import app_logger

logger = app_logger

# Tentative d'import de pywinauto (uniquement disponible sur Windows)
try:
    import pywinauto
    from pywinauto import Desktop, Application
    from pywinauto.findwindows import ElementNotFoundError
    from pywinauto.timings import TimeoutError as PywinautoTimeoutError

    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    logger.warning(
        "pywinauto non disponible. Le mode simulation sera utilisé."
    )


@dataclass
class DetectedMessage:
    """Message détecté dans l'interface WhatsApp."""
    contact_name: str
    content: str
    is_group: bool = False
    group_name: Optional[str] = None


class WhatsAppController:
    """Contrôleur pour interagir avec WhatsApp Desktop via UI Automation.

    Points de fragilité documentés:
    1. Le titre de la fenêtre peut changer selon la langue de Windows
    2. Les noms des contrôles UI dépendent de la version de WhatsApp
    3. La structure de l'arbre d'accessibilité peut varier

    Alternative robuste: Si l'automatisation UI échoue régulièrement,
    envisager l'utilisation de la capture d'écran + OCR (pytesseract)
    comme fallback pour la lecture des messages.
    """

    # Titres possibles de la fenêtre WhatsApp selon la langue
    WINDOW_TITLES = ["WhatsApp"]
    WINDOW_CLASS_NAME = None  # Auto-détecté

    def __init__(self, simulation_mode: bool = True):
        self.simulation_mode = simulation_mode
        self._app: Optional[object] = None
        self._main_window = None
        self._connected = False
        self._last_read_messages: dict[str, str] = {}

    @property
    def is_available(self) -> bool:
        """Vérifie si pywinauto est disponible."""
        return PYWINAUTO_AVAILABLE and not self.simulation_mode

    @property
    def is_connected(self) -> bool:
        """Vérifie si la connexion à WhatsApp est active."""
        if self.simulation_mode:
            return True
        return self._connected and self._main_window is not None

    def connect(self) -> bool:
        """Tente de se connecter à la fenêtre WhatsApp Desktop.

        Retourne True si la connexion est réussie.
        """
        if self.simulation_mode:
            logger.info("[SIMULATION] Connexion WhatsApp simulée")
            self._connected = True
            return True

        if not PYWINAUTO_AVAILABLE:
            logger.error("pywinauto n'est pas installé")
            return False

        try:
            # Tenter de trouver la fenêtre WhatsApp
            for title in self.WINDOW_TITLES:
                try:
                    self._app = Application(backend="uia").connect(
                        title_re=f".*{title}.*", timeout=5
                    )
                    self._main_window = self._app.window(title_re=f".*{title}.*")
                    self._main_window.wait("visible", timeout=5)
                    self._connected = True
                    logger.info("Connecté à WhatsApp Desktop (titre: %s)", title)
                    return True
                except (ElementNotFoundError, PywinautoTimeoutError):
                    continue

            logger.warning("WhatsApp Desktop non trouvé. Vérifiez qu'il est lancé.")
            self._connected = False
            return False

        except Exception as e:
            logger.error("Erreur connexion WhatsApp: %s", e)
            self._connected = False
            return False

    def disconnect(self):
        """Déconnecte du processus WhatsApp."""
        self._app = None
        self._main_window = None
        self._connected = False
        logger.info("Déconnecté de WhatsApp Desktop")

    def detect_unread_conversations(self) -> list[str]:
        """Détecte les conversations avec des messages non lus.

        Stratégie: Recherche les éléments de la liste de conversations
        qui contiennent un badge de notification (nombre de messages non lus).

        Point de fragilité: Le badge peut être un sous-élément avec un
        nom d'accessibilité variable.

        Retourne une liste de noms de contacts/groupes avec des messages non lus.
        """
        if self.simulation_mode:
            return self._simulate_unread_conversations()

        if not self.is_connected:
            logger.warning("Non connecté à WhatsApp")
            return []

        unread_contacts = []
        try:
            # Chercher le panneau de liste des conversations
            # La structure typique: fenêtre > panneau gauche > liste > éléments
            chat_list = self._find_chat_list()
            if not chat_list:
                logger.warning("Liste des conversations non trouvée")
                return []

            # Parcourir les éléments de la liste
            list_items = chat_list.children()
            for item in list_items:
                try:
                    # Vérifier la présence d'un badge de notification
                    item_name = item.window_text()
                    # Les conversations non lues ont souvent un texte contenant
                    # le nombre de messages non lus
                    children = item.children()
                    for child in children:
                        child_text = child.window_text()
                        if child_text and child_text.isdigit() and int(child_text) > 0:
                            # Extraire le nom du contact (premier texte de l'élément)
                            contact_name = self._extract_contact_name(item)
                            if contact_name:
                                unread_contacts.append(contact_name)
                            break
                except Exception:
                    continue

        except Exception as e:
            logger.error("Erreur détection messages non lus: %s", e)

        return unread_contacts

    def open_conversation(self, contact_name: str) -> bool:
        """Ouvre une conversation spécifique dans WhatsApp.

        Stratégie: Utilise la barre de recherche pour trouver le contact,
        puis clique sur le résultat.
        """
        if self.simulation_mode:
            logger.info("[SIMULATION] Ouverture conversation: %s", contact_name)
            return True

        if not self.is_connected:
            return False

        try:
            # Chercher la barre de recherche
            search_box = self._find_search_box()
            if not search_box:
                logger.warning("Barre de recherche WhatsApp non trouvée")
                return False

            # Cliquer et taper le nom du contact
            search_box.click_input()
            time.sleep(0.3)
            search_box.type_keys("^a")  # Sélectionner tout
            search_box.type_keys(contact_name, with_spaces=True)
            time.sleep(1)  # Attendre les résultats

            # Cliquer sur le premier résultat
            results = self._find_search_results()
            if results:
                results[0].click_input()
                time.sleep(0.5)
                # Effacer la recherche
                search_box.type_keys("{ESC}")
                logger.info("Conversation ouverte: %s", contact_name)
                return True

            logger.warning("Contact non trouvé: %s", contact_name)
            return False

        except Exception as e:
            logger.error("Erreur ouverture conversation %s: %s", contact_name, e)
            return False

    def read_last_message(self, contact_name: Optional[str] = None) -> Optional[DetectedMessage]:
        """Lit le dernier message de la conversation active.

        Stratégie: Accède au panneau de messages et lit le dernier élément.
        Filtre les messages envoyés par l'utilisateur.

        Point de fragilité: La distinction entre messages reçus et envoyés
        dépend de la structure UI (position, attributs d'accessibilité).
        """
        if self.simulation_mode:
            return self._simulate_read_message(contact_name)

        if not self.is_connected:
            return None

        try:
            # Trouver le panneau des messages
            msg_panel = self._find_message_panel()
            if not msg_panel:
                logger.warning("Panneau de messages non trouvé")
                return None

            # Récupérer les éléments de message
            messages = msg_panel.children()
            if not messages:
                return None

            # Parcourir depuis la fin pour trouver le dernier message reçu
            for msg_element in reversed(messages):
                try:
                    msg_text = msg_element.window_text().strip()
                    if not msg_text:
                        continue

                    # Vérifier que ce n'est pas un message système ou envoyé
                    if self._is_received_message(msg_element):
                        detected_contact = contact_name or self._get_active_contact_name()
                        return DetectedMessage(
                            contact_name=detected_contact or "Inconnu",
                            content=msg_text,
                        )
                except Exception:
                    continue

            return None

        except Exception as e:
            logger.error("Erreur lecture message: %s", e)
            return None

    def send_message(self, text: str) -> bool:
        """Envoie un message dans la conversation active.

        Stratégie: Trouve le champ de saisie, tape le texte et appuie sur Entrée.

        SÉCURITÉ: Cette méthode ne doit être appelée que si toutes les
        vérifications anti-boucle et anti-spam sont passées.
        """
        if self.simulation_mode:
            logger.info("[SIMULATION] Message envoyé: %s", text[:100])
            return True

        if not self.is_connected:
            return False

        if not text or not text.strip():
            logger.warning("Tentative d'envoi d'un message vide - ignoré")
            return False

        try:
            # Trouver le champ de saisie
            input_box = self._find_message_input()
            if not input_box:
                logger.warning("Champ de saisie WhatsApp non trouvé")
                return False

            # Cliquer sur le champ de saisie
            input_box.click_input()
            time.sleep(0.2)

            # Taper le message ligne par ligne (Shift+Enter pour les retours à la ligne)
            lines = text.split("\n")
            for i, line in enumerate(lines):
                input_box.type_keys(line, with_spaces=True, with_newlines=False)
                if i < len(lines) - 1:
                    input_box.type_keys("+{ENTER}")  # Shift+Enter pour nouvelle ligne

            time.sleep(0.2)
            # Appuyer sur Entrée pour envoyer
            input_box.type_keys("{ENTER}")

            logger.info("Message envoyé avec succès")
            return True

        except Exception as e:
            logger.error("Erreur envoi message: %s", e)
            return False

    def is_whatsapp_running(self) -> bool:
        """Vérifie si WhatsApp Desktop est lancé."""
        if self.simulation_mode:
            return True

        if not PYWINAUTO_AVAILABLE:
            return False

        try:
            for title in self.WINDOW_TITLES:
                try:
                    Application(backend="uia").connect(
                        title_re=f".*{title}.*", timeout=2
                    )
                    return True
                except (ElementNotFoundError, PywinautoTimeoutError):
                    continue
            return False
        except Exception:
            return False

    # --- Méthodes internes pour trouver les éléments UI ---

    def _find_chat_list(self):
        """Trouve la liste des conversations dans WhatsApp.

        Stratégie de recherche multicritère:
        1. Chercher par AutomationId si disponible
        2. Chercher par type de contrôle (List/ListItem)
        3. Chercher par position relative dans la fenêtre
        """
        if not self._main_window:
            return None
        try:
            # Tenter de trouver le panneau de la liste des chats
            # WhatsApp utilise généralement un contrôle de type "List" ou "Pane"
            pane = self._main_window.child_window(
                control_type="List", found_index=0
            )
            if pane.exists(timeout=2):
                return pane
        except Exception:
            pass

        try:
            # Alternative: chercher par le nom d'accessibilité
            pane = self._main_window.child_window(
                title="Chat list", control_type="List"
            )
            if pane.exists(timeout=2):
                return pane
        except Exception:
            pass

        return None

    def _find_search_box(self):
        """Trouve la barre de recherche WhatsApp."""
        if not self._main_window:
            return None
        try:
            search = self._main_window.child_window(
                control_type="Edit", found_index=0
            )
            if search.exists(timeout=2):
                return search
        except Exception:
            pass
        return None

    def _find_search_results(self) -> list:
        """Trouve les résultats de recherche."""
        if not self._main_window:
            return []
        try:
            results_list = self._main_window.child_window(
                control_type="List", found_index=0
            )
            if results_list.exists(timeout=2):
                return results_list.children()
        except Exception:
            pass
        return []

    def _find_message_panel(self):
        """Trouve le panneau contenant les messages de la conversation active."""
        if not self._main_window:
            return None
        try:
            # Chercher le panneau de messages (généralement le deuxième List)
            panel = self._main_window.child_window(
                control_type="List", found_index=1
            )
            if panel.exists(timeout=2):
                return panel
        except Exception:
            pass
        return None

    def _find_message_input(self):
        """Trouve le champ de saisie de message."""
        if not self._main_window:
            return None
        try:
            # Le champ de saisie est souvent le dernier Edit ou un RichEdit
            edits = self._main_window.children(control_type="Edit")
            if edits:
                # Prendre le dernier champ de saisie (celui du message)
                return edits[-1]
        except Exception:
            pass
        return None

    def _extract_contact_name(self, list_item) -> Optional[str]:
        """Extrait le nom du contact depuis un élément de liste."""
        try:
            text = list_item.window_text()
            if text:
                # Le nom est généralement la première ligne du texte
                return text.split("\n")[0].strip()
        except Exception:
            pass
        return None

    def _get_active_contact_name(self) -> Optional[str]:
        """Récupère le nom du contact de la conversation active."""
        if not self._main_window:
            return None
        try:
            # Le nom du contact actif est souvent dans le header du panneau droit
            header = self._main_window.child_window(
                control_type="Header", found_index=0
            )
            if header.exists(timeout=1):
                return header.window_text().strip()
        except Exception:
            pass
        return None

    def _is_received_message(self, msg_element) -> bool:
        """Détermine si un message est reçu (pas envoyé par nous).

        Heuristique: Les messages envoyés par l'utilisateur ont souvent
        des attributs différents (position, checkmarks, etc.).
        Cette méthode est un point de fragilité majeur.
        """
        try:
            # Heuristique basée sur la présence de checkmarks (ticks)
            # Les messages envoyés ont des icônes de statut (✓, ✓✓)
            children = msg_element.children()
            for child in children:
                text = child.window_text()
                if text and ("✓" in text or "Read" in text or "Delivered" in text):
                    return False  # Message envoyé
            return True
        except Exception:
            return True  # En cas de doute, considérer comme reçu

    # --- Méthodes de simulation pour le mode test ---

    _simulation_counter = 0
    _simulation_messages = [
        DetectedMessage(contact_name="Alice Martin", content="Bonjour ! Comment vas-tu ?"),
        DetectedMessage(contact_name="Bob Dupont", content="Tu peux m'envoyer le rapport ?"),
        DetectedMessage(
            contact_name="Groupe Projet",
            content="Réunion demain à 14h",
            is_group=True,
            group_name="Groupe Projet",
        ),
        DetectedMessage(contact_name="Claire Client", content="URGENT: Besoin d'un devis pour lundi"),
        DetectedMessage(contact_name="David Ami", content="On se fait un resto ce soir ? 😄"),
    ]

    def _simulate_unread_conversations(self) -> list[str]:
        """Simule la détection de conversations non lues."""
        import random

        contacts = ["Alice Martin", "Bob Dupont", "Groupe Projet", "Claire Client", "David Ami"]
        # Retourner aléatoirement 0 à 2 contacts
        count = random.randint(0, 2)
        selected = random.sample(contacts, min(count, len(contacts)))
        if selected:
            logger.info("[SIMULATION] Conversations non lues détectées: %s", selected)
        return selected

    def _simulate_read_message(self, contact_name: Optional[str] = None) -> Optional[DetectedMessage]:
        """Simule la lecture d'un message."""
        import random

        # Retourner un message simulé
        if contact_name:
            for msg in self._simulation_messages:
                if msg.contact_name == contact_name:
                    # Varier légèrement le contenu pour éviter les doublons
                    WhatsAppController._simulation_counter += 1
                    varied = DetectedMessage(
                        contact_name=msg.contact_name,
                        content=f"{msg.content} (#{WhatsAppController._simulation_counter})",
                        is_group=msg.is_group,
                        group_name=msg.group_name,
                    )
                    return varied

        msg = random.choice(self._simulation_messages)
        WhatsAppController._simulation_counter += 1
        return DetectedMessage(
            contact_name=msg.contact_name,
            content=f"{msg.content} (#{WhatsAppController._simulation_counter})",
            is_group=msg.is_group,
            group_name=msg.group_name,
        )
