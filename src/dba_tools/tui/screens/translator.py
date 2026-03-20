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
    """Screen interaktif untuk Translator AI (ID <-> EN)."""

    CSS_PATH = "../styles.tcss"

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+enter", "translate", "Translate"),
        Binding("ctrl+a", "select_all", "Select All"),
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

        self.direction = "id_to_en"  # "id_to_en" or "en_to_id"

    def compose(self) -> ComposeResult:
        with Container(id="main-container"):
            yield Static("[ MODULE: AI_TRANSLATOR ]", classes="header-area ascii-title")

            with Vertical(id="translator-form"):
                # Baris 1: Label Input & Tombol Copy + Select All
                with Horizontal(classes="label-row"):
                    yield Label(
                        "INPUT (Bahasa Indonesia):",
                        classes="menu-label",
                        id="label-input",
                    )
                    yield Button("COPY", id="btn-copy-in", classes="btn-copy")
                    yield Button("SELECT ALL", id="btn-select-in", classes="btn-copy")

                # TextArea Input
                yield TextArea(id="input-id", soft_wrap=True)

                # Baris Tombol: Swap & Translate
                with Horizontal(classes="label-row"):
                    yield Button("SWAP ⇄", id="btn-swap", classes="btn-swap")
                    yield Button("TRANSLATE TO FORMAL ENGLISH", id="btn-translate")

                # Baris 2: Label Output & Tombol Copy + Select All
                with Horizontal(classes="label-row"):
                    yield Label(
                        "OUTPUT (Formal English):",
                        classes="menu-label",
                        id="label-output",
                    )
                    yield Button("COPY", id="btn-copy-out", classes="btn-copy")
                    yield Button("SELECT ALL", id="btn-select-out", classes="btn-copy")

                # TextArea Output
                yield TextArea(id="output-en", read_only=True, soft_wrap=True)

            yield Label(
                "\[ESC] BACK | \[CTRL+ENTER] TRANSLATE | \[CTRL+A] SELECT ALL",
                classes="footer-text",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        # Handler untuk tombol Translate
        if btn_id == "btn-translate":
            self.process_translation()

        # Handler untuk tombol Swap
        elif btn_id == "btn-swap":
            self.swap_direction()

        # Handler untuk Select All Input
        elif btn_id == "btn-select-in":
            self.select_all_text("#input-id")

        # Handler untuk Select All Output
        elif btn_id == "btn-select-out":
            self.select_all_text("#output-en")

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

    def action_select_all(self) -> None:
        """Handler untuk Ctrl+A - select all di input."""
        self.select_all_text("#input-id")

    def swap_direction(self) -> None:
        """Menukar arah terjemahan antara ID->EN dan EN->ID."""
        if self.direction == "id_to_en":
            self.direction = "en_to_id"
            self.notify("Arah: English -> Indonesia", severity="information")
        else:
            self.direction = "id_to_en"
            self.notify("Arah: Indonesia -> English", severity="information")
        self.update_labels()
        self.update_translate_button()

    def update_translate_button(self) -> None:
        """Memperbarui teks tombol translate berdasarkan arah."""
        translate_btn = self.query_one("#btn-translate", Button)
        if self.direction == "id_to_en":
            translate_btn.label = "TRANSLATE TO FORMAL ENGLISH"
        else:
            translate_btn.label = "TRANSLATE TO INDONESIAN"

    def select_all_text(self, widget_id: str) -> None:
        """Memilih semua teks di TextArea."""
        text_area = self.query_one(widget_id, TextArea)
        text_area.focus()
        text_area.select_all()

    def update_labels(self) -> None:
        """Memperbarui label berdasarkan arah terjemahan."""
        input_label = self.query_one("#label-input", Label)
        output_label = self.query_one("#label-output", Label)

        if self.direction == "id_to_en":
            input_label.update("INPUT (Bahasa Indonesia):")
            output_label.update("OUTPUT (Formal English):")
        else:
            input_label.update("INPUT (Formal English):")
            output_label.update("OUTPUT (Bahasa Indonesia):")

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

        if self.direction == "id_to_en":
            prompt = (
                "Anda adalah penerjemah profesional. Terjemahkan teks bahasa Indonesia berikut "
                "ke bahasa Inggris. Gunakan tata bahasa (grammar) yang tepat, gaya bahasa yang sangat formal, "
                "dan profesional. Jangan tambahkan penjelasan apapun, cukup berikan hasil terjemahannya saja. "
                f"Teks: '{text_to_translate}'"
            )
        else:
            prompt = (
                "You are a professional translator. Translate the following English text "
                "to Indonesian (Bahasa Indonesia). Use proper grammar and natural, professional language. "
                "Do not add any explanations, just provide the translation. "
                f"Text: '{text_to_translate}'"
            )

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            result_text = (
                response.text.strip()
                if response.text
                else "No translation returned from AI."
            )

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
