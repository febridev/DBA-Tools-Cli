import os

from dotenv import load_dotenv
from google import genai
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding

# Tambahkan Horizontal di sini
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static, TextArea


class TranslatorScreen(Screen):
    """Screen interaktif untuk Translator AI (ID -> Formal EN)."""

    CSS_PATH = "../styles.tcss"

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("f5", "translate", "Translate"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        load_dotenv(override=True)
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()

        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
            self.notify("API Key KOSONG! Cek file .env", severity="error")

    def compose(self) -> ComposeResult:
        with Container(id="main-container"):
            yield Static("[ MODULE: AI_TRANSLATOR ]", classes="header-area ascii-title")

            with Vertical(id="translator-form"):

                # Baris 1: Label Input & Tombol Copy
                with Horizontal(classes="label-row"):
                    yield Label("INPUT (Bahasa Indonesia):", classes="menu-label")
                    yield Button("COPY", id="btn-copy-in", classes="btn-copy")

                # TextArea Input
                yield TextArea(id="input-id", soft_wrap=True)

                # Tombol Translate Utama
                yield Button("TRANSLATE TO FORMAL ENGLISH", id="btn-translate")

                # Baris 2: Label Output & Tombol Copy
                with Horizontal(classes="label-row"):
                    yield Label("OUTPUT (Formal English):", classes="menu-label")
                    yield Button("COPY", id="btn-copy-out", classes="btn-copy")

                # TextArea Output
                yield TextArea(id="output-en", read_only=True, soft_wrap=True)

            yield Label("\[ESC] BACK | \[F5] TRANSLATE", classes="footer-text")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        # Handler untuk tombol Translate
        if btn_id == "btn-translate":
            self.process_translation()

        # Handler untuk tombol Copy Input
        elif btn_id == "btn-copy-in":
            text = self.query_one("#input-id", TextArea).text.strip()
            if text:
                self.app.copy_to_clipboard(text)
                self.notify("Input disalin ke clipboard!", severity="information")
            else:
                self.notify("Input kosong, tidak ada yang disalin.", severity="warning")

        # Handler untuk tombol Copy Output
        elif btn_id == "btn-copy-out":
            text = self.query_one("#output-en", TextArea).text.strip()
            if text:
                self.app.copy_to_clipboard(text)
                self.notify(
                    "Hasil terjemahan disalin ke clipboard!", severity="information"
                )
            else:
                self.notify(
                    "Output kosong, tidak ada yang disalin.", severity="warning"
                )

    def action_translate(self) -> None:
        """Handler untuk membaca hotkey F5 dari keyboard."""
        self.process_translation()

    @work(exclusive=True, thread=True)
    def process_translation(self) -> None:
        input_widget = self.query_one("#input-id", TextArea)
        output_widget = self.query_one("#output-en", TextArea)

        text_to_translate = input_widget.text.strip()

        if not text_to_translate:
            self.app.call_from_thread(
                self.notify, "Teks tidak boleh kosong!", severity="error"
            )
            return

        if not self.client:
            self.app.call_from_thread(
                output_widget.load_text, "ERROR: GEMINI_API_KEY tidak ditemukan."
            )
            return

        self.app.call_from_thread(
            output_widget.load_text, "Mengirim ke AI... Mohon tunggu sebentar."
        )

        prompt = (
            "Anda adalah penerjemah profesional. Terjemahkan teks bahasa Indonesia berikut "
            "ke bahasa Inggris. Gunakan tata bahasa (grammar) yang tepat, gaya bahasa yang sangat formal, "
            f"dan profesional. Jangan tambahkan penjelasan apapun, cukup berikan hasil terjemahannya saja. Teks: '{text_to_translate}'"
        )

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            result_text = response.text.strip()

            self.app.call_from_thread(output_widget.load_text, result_text)
            self.app.call_from_thread(
                self.notify, "Berhasil diterjemahkan!", severity="information"
            )

        except Exception as e:
            error_msg = f"Error: {str(e)}\n\nPastikan API Key Anda valid."
            self.app.call_from_thread(output_widget.load_text, error_msg)
            self.app.call_from_thread(
                self.notify, "Gagal memproses terjemahan.", severity="error"
            )
