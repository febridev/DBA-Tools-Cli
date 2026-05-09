import json
import os
import time

import requests
from dotenv import load_dotenv

# from google import genai
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding

# Add Horizontal here
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, LoadingIndicator, Static, TextArea


class TranslatorScreen(Screen):
    """Interactive screen for Translator AI (ID <-> EN)."""

    CSS_PATH = "../styles.tcss"

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+enter", "translate", "Translate"),
        Binding("ctrl+a", "select_all", "Select All"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        load_dotenv(override=True)

        # Load configuration from .env
        self.api_key = os.environ.get("GEMINI_API_KEY", "dummy_key").strip()

        # Load 9router URL, use default localhost:8000 if not set in .env
        self.router_url = os.environ.get("ROUTER_URL", "http://127.0.0.1:8000").strip()

        self.direction = "id_to_en"  # "id_to_en" or "en_to_id"

    def compose(self) -> ComposeResult:
        with Container(id="main-container"):
            yield Static("[ MODULE: AI_TRANSLATOR ]", classes="header-area ascii-title")

            with Vertical(id="translator-form"):
                # Row 1: Input label and Copy + Select All buttons
                with Horizontal(classes="label-row"):
                    yield Label(
                        "INPUT (Indonesian):",
                        classes="menu-label",
                        id="label-input",
                    )
                    yield Button("COPY", id="btn-copy-in", classes="btn-copy")
                    yield Button("SELECT ALL", id="btn-select-in", classes="btn-copy")

                # Input TextArea
                yield TextArea(id="input-id", soft_wrap=True)

                # Loading Indicators (Hidden by default)
                yield LoadingIndicator(id="loading-indicator")
                yield Label("", id="status-text")

                # Button row: Swap & Translate
                with Horizontal(classes="label-row"):
                    yield Button("SWAP ⇄", id="btn-swap", classes="btn-swap")
                    yield Button("TRANSLATE TO FORMAL ENGLISH", id="btn-translate")

                # Row 2: Output label and Copy + Select All buttons
                with Horizontal(classes="label-row"):
                    yield Label(
                        "OUTPUT (Formal English):",
                        classes="menu-label",
                        id="label-output",
                    )
                    yield Button("COPY", id="btn-copy-out", classes="btn-copy")
                    yield Button("SELECT ALL", id="btn-select-out", classes="btn-copy")

                # Output TextArea
                yield TextArea(id="output-en", read_only=True, soft_wrap=True)

            yield Label(
                "[ESC] BACK | [CTRL+ENTER] TRANSLATE | [CTRL+A] SELECT ALL",
                classes="footer-text",
            )

    def on_mount(self) -> None:
        """Focus the input text area when the screen is mounted."""
        self.query_one("#input-id").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        # Handler for Translate button
        if btn_id == "btn-translate":
            self.process_translation()

        # Handler for Swap button
        elif btn_id == "btn-swap":
            self.swap_direction()

        # Handler for Select All Input button
        elif btn_id == "btn-select-in":
            self.select_all_text("#input-id")

        # Handler for Select All Output button
        elif btn_id == "btn-select-out":
            self.select_all_text("#output-en")

        # Handler for Copy Input button
        elif btn_id == "btn-copy-in":
            text = self.query_one("#input-id", TextArea).text.strip()
            if text:
                self.app.copy_to_clipboard(text)
                self.notify("Import copied to clipboard!", severity="information")
            else:
                self.notify("Input is empty, nothing to copy.", severity="warning")

        # Handler for Copy Output button
        elif btn_id == "btn-copy-out":
            text = self.query_one("#output-en", TextArea).text.strip()
            if text:
                self.app.copy_to_clipboard(text)
                self.notify(
                    "Translation result copied to clipboard!", severity="information"
                )
            else:
                self.notify("Output is empty, nothing to copy.", severity="warning")

    def action_translate(self) -> None:
        """Handler for F5 hotkey from keyboard."""
        self.process_translation()

    def select_all_text(self, widget_id: str) -> None:
        """Select all text in the given TextArea widget."""
        text_area = self.query_one(widget_id, TextArea)
        if text_area:
            text_area.focus()
            text_area.select_all()

    def action_select_all(self) -> None:
        """Handler for Ctrl+A - select all in input."""
        self.select_all_text("#input-id")

    def swap_direction(self) -> None:
        """Swap translation direction between ID->EN and EN->ID."""
        if self.direction == "id_to_en":
            self.direction = "en_to_id"
            self.notify("Direction: English -> Indonesian", severity="information")
        else:
            self.direction = "id_to_en"
            self.notify("Direction: Indonesian -> English", severity="information")
        self.update_labels()
        self.update_translate_button()

    def update_translate_button(self) -> None:
        """Update translate button text based on translation direction."""
        translate_btn = self.query_one("#btn-translate", Button)
        if self.direction == "id_to_en":
            translate_btn.label = "TRANSLATE TO FORMAL ENGLISH"
        else:
            translate_btn.label = "TRANSLATE TO INDONESIAN"

    def update_labels(self) -> None:
        """Update labels based on translation direction."""
        input_label = self.query_one("#label-input", Label)
        output_label = self.query_one("#label-output", Label)

        if self.direction == "id_to_en":
            input_label.update("INPUT (Indonesian):")
            output_label.update("OUTPUT (Formal English):")
        else:
            input_label.update("INPUT (Formal English):")
            output_label.update("OUTPUT (Indonesian):")

    @work(exclusive=True, thread=True)
    def process_translation(self) -> None:
        input_widget = self.query_one("#input-id", TextArea)
        output_widget = self.query_one("#output-en", TextArea)
        loading_indicator = self.query_one("#loading-indicator", LoadingIndicator)
        status_text = self.query_one("#status-text", Label)

        text_to_translate = input_widget.text.strip()

        if not text_to_translate:
            self.app.call_from_thread(
                self.notify, "Text cannot be empty!", severity="error"
            )
            return

        self.app.call_from_thread(
            output_widget.load_text, "Translating... Please wait."
        )
        
        # Show and reset loading indicator/status
        def setup_ui():
            loading_indicator.styles.display = "block"
            status_text.styles.display = "block"
            status_text.update("Starting translation...")
        self.app.call_from_thread(setup_ui)

        if self.direction == "id_to_en":
            prompt = (
                "You are a professional translator. Translate the following Indonesian text "
                "into English. Use a natural and polished style that is professional yet easy to read, "
                "suitable for both formal and business-casual contexts. "
                "Do not add any explanations, just provide the translation result. "
                f"Text: '{text_to_translate}'"
            )
        else:
            prompt = (
                "You are a professional translator. Translate the following English text "
                "into natural Indonesian (Bahasa Indonesia). Use a style that is polite and professional "
                "but remains easy to understand. "
                "Do not add any explanations, just provide the translation. "
                f"Text: '{text_to_translate}'"
            )

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Available models to try in order of priority
            available_models = [
                "gc/gemini-3-flash-preview",
                "anthropic/claude-3-opus",
                "openai/gpt-4-turbo",
            ]

            result_text = None
            selected_model = None
            max_attempts = 10
            retry_delay = 2

            for attempt in range(max_attempts):
                # Update status text
                self.app.call_from_thread(
                    status_text.update, f"Translating... (Attempt {attempt + 1}/{max_attempts})"
                )
                
                # Cycle through models
                model = available_models[attempt % len(available_models)]
                
                payload = {
                    "model": model,
                    "stream": False,
                    "messages": [{"role": "user", "content": prompt}],
                }

                try:
                    response = requests.post(
                        self.router_url, headers=headers, json=payload, timeout=30
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("choices"):
                            content = data["choices"][0].get("message", {}).get("content", "").strip()
                            if content:
                                result_text = content
                                selected_model = model
                                break
                except Exception:
                    pass

                if attempt < max_attempts - 1:
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 10) # Exponential backoff capped at 10s

            # Hide indicators when done
            def cleanup_ui():
                loading_indicator.styles.display = "none"
                status_text.styles.display = "none"
            self.app.call_from_thread(cleanup_ui)

            self.app.call_from_thread(
                output_widget.load_text,
                result_text if result_text else "Empty translation after multiple attempts.",
            )
            
            if result_text:
                self.app.call_from_thread(
                    self.notify,
                    f"Successfully translated using {selected_model}!",
                    severity="information",
                )
            else:
                self.app.call_from_thread(
                    self.notify,
                    "Failed to get a translation after 10 attempts.",
                    severity="error",
                )

        except Exception as e:
            def error_cleanup_ui():
                loading_indicator.styles.display = "none"
                status_text.styles.display = "none"
            self.app.call_from_thread(error_cleanup_ui)
            error_msg = f"Connection Error: {str(e)}\n\nPlease ensure 9Router is running and the URL in .env is correct."
            self.app.call_from_thread(output_widget.load_text, error_msg)
            self.app.call_from_thread(
                self.notify, "Failed to process translation.", severity="error"
            )
