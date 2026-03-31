"""Interface utilisateur principale avec customtkinter.

Affiche:
- Statut WhatsApp et surveillance
- Liste des messages traités
- Réponses IA proposées avec actions
- Panneau de paramètres
- Zone de logs
"""

import threading
import tkinter as tk
from datetime import datetime
from typing import Optional

try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False

from app.models.message import GeneratedResponse, IncomingMessage, ResponseStatus


class MainWindow:
    """Fenêtre principale de l'application."""

    def __init__(self, app_controller):
        """
        Args:
            app_controller: Instance de AppController qui gère la logique métier.
        """
        self.controller = app_controller

        if not CTK_AVAILABLE:
            raise ImportError(
                "customtkinter n'est pas installé. "
                "Installez-le avec: pip install customtkinter"
            )

        # Configuration de customtkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Fenêtre principale
        self.root = ctk.CTk()
        self.root.title("WhatsApp Desktop Assistant")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        # Variables UI
        self._status_var = tk.StringVar(value="Déconnecté")
        self._mode_var = tk.StringVar(value="draft_only")
        self._provider_var = tk.StringVar(value="mock")
        self._tone_var = tk.StringVar(value="neutral")
        self._delay_var = tk.StringVar(value="5")
        self._whitelist_var = tk.StringVar(value="")
        self._blacklist_var = tk.StringVar(value="")
        self._system_prompt_var = tk.StringVar(value="")
        self._simulation_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._setup_callbacks()

    def _build_ui(self):
        """Construit l'interface utilisateur."""
        # Layout principal: 2 colonnes
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # --- Header ---
        self._build_header()

        # --- Zone principale (gauche) ---
        main_frame = ctk.CTkFrame(self.root)
        main_frame.grid(row=1, column=0, padx=(10, 5), pady=(0, 10), sticky="nsew")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        self._build_messages_panel(main_frame)
        self._build_logs_panel(main_frame)

        # --- Panneau latéral (droite) ---
        side_frame = ctk.CTkFrame(self.root)
        side_frame.grid(row=1, column=1, padx=(5, 10), pady=(0, 10), sticky="nsew")
        self._build_settings_panel(side_frame)

    def _build_header(self):
        """Construit la barre d'en-tête avec statut et contrôles."""
        header = ctk.CTkFrame(self.root, height=60)
        header.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        header.grid_columnconfigure(2, weight=1)

        # Indicateur de statut WhatsApp
        self._status_indicator = ctk.CTkLabel(
            header, text="●", font=("Arial", 20), text_color="red"
        )
        self._status_indicator.grid(row=0, column=0, padx=(10, 5), pady=10)

        self._status_label = ctk.CTkLabel(
            header,
            textvariable=self._status_var,
            font=("Arial", 14, "bold"),
        )
        self._status_label.grid(row=0, column=1, padx=5, pady=10)

        # Spacer
        ctk.CTkLabel(header, text="").grid(row=0, column=2)

        # Boutons de contrôle
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=3, padx=10, pady=10)

        self._btn_start = ctk.CTkButton(
            btn_frame, text="Démarrer", width=100, command=self._on_start,
            fg_color="green", hover_color="darkgreen"
        )
        self._btn_start.grid(row=0, column=0, padx=3)

        self._btn_pause = ctk.CTkButton(
            btn_frame, text="Pause", width=80, command=self._on_pause,
            fg_color="orange", hover_color="darkorange", state="disabled"
        )
        self._btn_pause.grid(row=0, column=1, padx=3)

        self._btn_stop = ctk.CTkButton(
            btn_frame, text="Arrêter", width=80, command=self._on_stop,
            fg_color="gray", state="disabled"
        )
        self._btn_stop.grid(row=0, column=2, padx=3)

        self._btn_emergency = ctk.CTkButton(
            btn_frame, text="STOP URGENCE", width=120, command=self._on_emergency,
            fg_color="darkred", hover_color="red"
        )
        self._btn_emergency.grid(row=0, column=3, padx=3)

    def _build_messages_panel(self, parent):
        """Construit le panneau des messages et réponses."""
        # Conteneur avec onglets
        tabview = ctk.CTkTabview(parent)
        tabview.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Onglet Messages
        tab_msgs = tabview.add("Messages reçus")
        tab_msgs.grid_columnconfigure(0, weight=1)
        tab_msgs.grid_rowconfigure(0, weight=1)

        self._messages_text = ctk.CTkTextbox(tab_msgs, font=("Consolas", 12))
        self._messages_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self._messages_text.configure(state="disabled")

        # Onglet Réponses
        tab_resp = tabview.add("Réponses IA")
        tab_resp.grid_columnconfigure(0, weight=1)
        tab_resp.grid_rowconfigure(0, weight=1)

        resp_container = ctk.CTkFrame(tab_resp)
        resp_container.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        resp_container.grid_columnconfigure(0, weight=1)
        resp_container.grid_rowconfigure(0, weight=1)

        self._responses_text = ctk.CTkTextbox(resp_container, font=("Consolas", 12))
        self._responses_text.grid(row=0, column=0, padx=5, pady=(5, 0), sticky="nsew")
        self._responses_text.configure(state="disabled")

        # Boutons d'action pour les réponses
        action_frame = ctk.CTkFrame(resp_container, fg_color="transparent")
        action_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self._response_id_var = tk.StringVar(value="")
        ctk.CTkLabel(action_frame, text="ID réponse:").grid(row=0, column=0, padx=5)
        self._response_id_entry = ctk.CTkEntry(
            action_frame, textvariable=self._response_id_var, width=60
        )
        self._response_id_entry.grid(row=0, column=1, padx=5)

        ctk.CTkButton(
            action_frame, text="Valider et envoyer", width=140,
            command=self._on_approve, fg_color="green", hover_color="darkgreen"
        ).grid(row=0, column=2, padx=5)

        ctk.CTkButton(
            action_frame, text="Ignorer", width=80,
            command=self._on_ignore, fg_color="gray"
        ).grid(row=0, column=3, padx=5)

        ctk.CTkButton(
            action_frame, text="Réessayer lecture", width=130,
            command=self._on_retry
        ).grid(row=0, column=4, padx=5)

    def _build_logs_panel(self, parent):
        """Construit le panneau de logs."""
        log_frame = ctk.CTkFrame(parent)
        log_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            log_frame, text="Journal d'activité", font=("Arial", 13, "bold")
        ).grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self._log_text = ctk.CTkTextbox(
            log_frame, font=("Consolas", 11), height=150
        )
        self._log_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self._log_text.configure(state="disabled")

    def _build_settings_panel(self, parent):
        """Construit le panneau de paramètres."""
        parent.grid_columnconfigure(0, weight=1)

        # Titre
        ctk.CTkLabel(
            parent, text="Paramètres", font=("Arial", 15, "bold")
        ).grid(row=0, column=0, padx=10, pady=10)

        # Scrollable frame pour les paramètres
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        parent.grid_rowconfigure(1, weight=1)
        scroll.grid_columnconfigure(0, weight=1)

        row = 0

        # Mode simulation
        ctk.CTkLabel(scroll, text="Mode simulation:").grid(
            row=row, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        row += 1
        ctk.CTkSwitch(
            scroll, text="Simulation active",
            variable=self._simulation_var,
            command=self._on_simulation_toggle
        ).grid(row=row, column=0, padx=10, pady=5, sticky="w")
        row += 1

        # Mode de réponse
        ctk.CTkLabel(scroll, text="Mode de réponse:").grid(
            row=row, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        row += 1
        ctk.CTkOptionMenu(
            scroll,
            values=["draft_only", "manual_validation", "auto_reply"],
            variable=self._mode_var,
            command=self._on_mode_change,
        ).grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        row += 1

        # Provider IA
        ctk.CTkLabel(scroll, text="Provider IA:").grid(
            row=row, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        row += 1
        ctk.CTkOptionMenu(
            scroll,
            values=["mock", "openai", "anthropic"],
            variable=self._provider_var,
            command=self._on_provider_change,
        ).grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        row += 1

        # Ton
        ctk.CTkLabel(scroll, text="Ton par défaut:").grid(
            row=row, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        row += 1
        ctk.CTkOptionMenu(
            scroll,
            values=["neutral", "professional", "friendly", "casual", "formal"],
            variable=self._tone_var,
            command=self._on_tone_change,
        ).grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        row += 1

        # Délai de réponse
        ctk.CTkLabel(scroll, text="Délai réponse (sec):").grid(
            row=row, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        row += 1
        ctk.CTkEntry(scroll, textvariable=self._delay_var).grid(
            row=row, column=0, padx=10, pady=5, sticky="ew"
        )
        row += 1

        # Whitelist
        ctk.CTkLabel(scroll, text="Whitelist (un par ligne):").grid(
            row=row, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        row += 1
        self._whitelist_text = ctk.CTkTextbox(scroll, height=80, font=("Consolas", 11))
        self._whitelist_text.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        row += 1

        # Blacklist
        ctk.CTkLabel(scroll, text="Blacklist (un par ligne):").grid(
            row=row, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        row += 1
        self._blacklist_text = ctk.CTkTextbox(scroll, height=80, font=("Consolas", 11))
        self._blacklist_text.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        row += 1

        # Prompt système
        ctk.CTkLabel(scroll, text="Prompt système:").grid(
            row=row, column=0, padx=10, pady=(10, 0), sticky="w"
        )
        row += 1
        self._prompt_text = ctk.CTkTextbox(scroll, height=100, font=("Consolas", 11))
        self._prompt_text.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
        row += 1

        # Bouton appliquer
        ctk.CTkButton(
            scroll, text="Appliquer les paramètres",
            command=self._on_apply_settings
        ).grid(row=row, column=0, padx=10, pady=15, sticky="ew")

    def _setup_callbacks(self):
        """Configure les callbacks du contrôleur vers l'UI."""
        self.controller.set_ui_callbacks(
            on_new_message=self._on_message_received,
            on_response_ready=self._on_response_generated,
            on_status_change=self._on_status_changed,
            on_alert=self._on_alert_received,
            on_log=self._on_log_entry,
        )

    # --- Mise à jour UI thread-safe ---

    def _update_ui(self, func, *args):
        """Exécute une mise à jour UI de manière thread-safe."""
        try:
            self.root.after(0, func, *args)
        except Exception:
            pass

    def _on_message_received(self, msg: IncomingMessage):
        """Callback quand un nouveau message est reçu."""
        self._update_ui(self._append_message, msg)

    def _on_response_generated(self, resp: GeneratedResponse):
        """Callback quand une réponse est générée."""
        self._update_ui(self._append_response, resp)

    def _on_status_changed(self, status: str):
        """Callback quand le statut change."""
        self._update_ui(self._set_status, status)

    def _on_alert_received(self, contact: str, message: str):
        """Callback pour les alertes urgentes."""
        self._update_ui(self._show_alert, contact, message)

    def _on_log_entry(self, text: str):
        """Callback pour les entrées de log."""
        self._update_ui(self._append_log, text)

    def _append_message(self, msg: IncomingMessage):
        """Ajoute un message à la liste."""
        self._messages_text.configure(state="normal")
        timestamp = msg.timestamp.strftime("%H:%M:%S")
        group_info = f" [{msg.group_name}]" if msg.is_group else ""
        line = f"[{timestamp}] {msg.contact_name}{group_info}: {msg.content}\n"
        self._messages_text.insert("end", line)
        self._messages_text.see("end")
        self._messages_text.configure(state="disabled")

    def _append_response(self, resp: GeneratedResponse):
        """Ajoute une réponse à la liste."""
        self._responses_text.configure(state="normal")
        timestamp = resp.timestamp.strftime("%H:%M:%S")
        status_icon = {
            ResponseStatus.DRAFT: "[BROUILLON]",
            ResponseStatus.APPROVED: "[APPROUVE]",
            ResponseStatus.SENT: "[ENVOYE]",
            ResponseStatus.IGNORED: "[IGNORE]",
            ResponseStatus.ERROR: "[ERREUR]",
        }.get(resp.status, "[?]")

        lines = (
            f"\n{'='*60}\n"
            f"[{timestamp}] #{resp.id} | {resp.contact_name} | {status_icon}\n"
            f"Message: {resp.original_message[:100]}\n"
            f"Réponse ({resp.provider}): {resp.response_text}\n"
        )
        self._responses_text.insert("end", lines)
        self._responses_text.see("end")
        self._responses_text.configure(state="disabled")

        # Pré-remplir l'ID de réponse
        self._response_id_var.set(str(resp.id))

    def _append_log(self, text: str):
        """Ajoute une ligne au journal."""
        self._log_text.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_text.insert("end", f"[{timestamp}] {text}\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _set_status(self, status: str):
        """Met à jour l'indicateur de statut."""
        status_map = {
            "running": ("Surveillance active", "green"),
            "paused": ("En pause", "orange"),
            "stopped": ("Arrêté", "gray"),
            "emergency_stopped": ("ARRÊT URGENCE", "red"),
            "connected": ("Connecté", "green"),
            "disconnected": ("Déconnecté", "red"),
        }
        text, color = status_map.get(status, ("Inconnu", "gray"))
        self._status_var.set(text)
        self._status_indicator.configure(text_color=color)

        # Mettre à jour les boutons
        is_running = status in ("running", "paused")
        self._btn_start.configure(state="disabled" if is_running else "normal")
        self._btn_pause.configure(
            state="normal" if status == "running" else "disabled",
            text="Reprendre" if status == "paused" else "Pause",
        )
        self._btn_stop.configure(state="normal" if is_running else "disabled")

    def _show_alert(self, contact: str, message: str):
        """Affiche une alerte pour un message urgent."""
        # Utiliser une boîte de dialogue
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("ALERTE - Message urgent")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Message URGENT reçu !",
            font=("Arial", 16, "bold"), text_color="red"
        ).pack(pady=10)

        ctk.CTkLabel(dialog, text=f"De: {contact}").pack(pady=5)
        ctk.CTkLabel(dialog, text=f"Message: {message[:200]}", wraplength=350).pack(pady=5)

        ctk.CTkButton(dialog, text="OK", command=dialog.destroy).pack(pady=15)

    # --- Handlers boutons ---

    def _on_start(self):
        self.controller.start_monitoring()
        self._append_log("Surveillance démarrée")

    def _on_pause(self):
        if self.controller.is_paused():
            self.controller.resume_monitoring()
            self._append_log("Surveillance reprise")
        else:
            self.controller.pause_monitoring()
            self._append_log("Surveillance en pause")

    def _on_stop(self):
        self.controller.stop_monitoring()
        self._append_log("Surveillance arrêtée")

    def _on_emergency(self):
        self.controller.emergency_stop()
        self._append_log("ARRÊT D'URGENCE activé")

    def _on_approve(self):
        try:
            resp_id = int(self._response_id_var.get())
            success = self.controller.approve_response(resp_id)
            if success:
                self._append_log(f"Réponse #{resp_id} envoyée")
            else:
                self._append_log(f"Échec envoi réponse #{resp_id}")
        except ValueError:
            self._append_log("ID de réponse invalide")

    def _on_ignore(self):
        try:
            resp_id = int(self._response_id_var.get())
            self.controller.ignore_response(resp_id)
            self._append_log(f"Réponse #{resp_id} ignorée")
        except ValueError:
            self._append_log("ID de réponse invalide")

    def _on_retry(self):
        self._append_log("Relecture demandée...")
        threading.Thread(
            target=self.controller.retry_last_contact, daemon=True
        ).start()

    def _on_simulation_toggle(self):
        self.controller.set_simulation_mode(self._simulation_var.get())
        mode = "activé" if self._simulation_var.get() else "désactivé"
        self._append_log(f"Mode simulation {mode}")

    def _on_mode_change(self, value):
        self.controller.set_response_mode(value)
        self._append_log(f"Mode de réponse: {value}")

    def _on_provider_change(self, value):
        self.controller.set_ai_provider(value)
        self._append_log(f"Provider IA: {value}")

    def _on_tone_change(self, value):
        self.controller.set_default_tone(value)
        self._append_log(f"Ton par défaut: {value}")

    def _on_apply_settings(self):
        """Applique tous les paramètres."""
        # Délai
        try:
            delay = int(self._delay_var.get())
            self.controller.set_response_delay(delay)
        except ValueError:
            self._append_log("Délai invalide")

        # Whitelist
        whitelist_text = self._whitelist_text.get("1.0", "end").strip()
        whitelist = [w.strip() for w in whitelist_text.split("\n") if w.strip()]

        # Blacklist
        blacklist_text = self._blacklist_text.get("1.0", "end").strip()
        blacklist = [b.strip() for b in blacklist_text.split("\n") if b.strip()]

        self.controller.update_lists(whitelist, blacklist)

        # Prompt système
        prompt = self._prompt_text.get("1.0", "end").strip()
        if prompt:
            self.controller.set_system_prompt(prompt)

        self._append_log("Paramètres appliqués")

    def load_settings(self, settings: dict):
        """Charge les paramètres dans l'UI."""
        if "response_mode" in settings:
            self._mode_var.set(settings["response_mode"])
        if "ai_provider" in settings:
            self._provider_var.set(settings["ai_provider"])
        if "default_tone" in settings:
            self._tone_var.set(settings["default_tone"])
        if "response_delay" in settings:
            self._delay_var.set(str(settings["response_delay"]))
        if "simulation_mode" in settings:
            self._simulation_var.set(settings["simulation_mode"])
        if "system_prompt" in settings:
            self._prompt_text.delete("1.0", "end")
            self._prompt_text.insert("1.0", settings["system_prompt"])
        if "whitelist" in settings:
            self._whitelist_text.delete("1.0", "end")
            self._whitelist_text.insert("1.0", "\n".join(settings["whitelist"]))
        if "blacklist" in settings:
            self._blacklist_text.delete("1.0", "end")
            self._blacklist_text.insert("1.0", "\n".join(settings["blacklist"]))

    def run(self):
        """Lance la boucle principale de l'interface."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        """Gestion de la fermeture de la fenêtre."""
        self.controller.stop_monitoring()
        self.root.destroy()
