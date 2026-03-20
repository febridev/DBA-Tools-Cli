import os

from dotenv import load_dotenv
from google import genai
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static, TextArea


class AWRAnalyzerScreen(Screen):
    """Screen untuk analisis AWR Oracle menggunakan AI."""

    CSS_PATH = "../styles.tcss"

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+enter", "analyze", "Analyze"),
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
            yield Static(
                "[ MODULE: ORACLE AWR ANALYSIS ]", classes="header-area ascii-title"
            )

            with Vertical(id="awr-form"):
                yield Label(
                    "Input AWR File Paths (one per line):", classes="menu-label"
                )

                yield TextArea(
                    id="awr-paths",
                    placeholder="Enter full paths to AWR report files (HTML or text format)...",
                    soft_wrap=True,
                )

                yield Button("ANALYZE AWR REPORTS", id="btn-analyze")

                with Horizontal(classes="label-row"):
                    yield Label("Analysis Results:", classes="menu-label")
                    yield Button(
                        "SELECT ALL", id="btn-select-results", classes="btn-copy"
                    )
                    yield Button("COPY ALL", id="btn-copy-results", classes="btn-copy")

                yield TextArea(id="awr-results", read_only=True, soft_wrap=True)

            yield Label("\[ESC] BACK | \[CTRL+ENTER] ANALYZE", classes="footer-text")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "btn-analyze":
            self.analyze_awr()
        elif btn_id == "btn-select-results":
            self.select_all_text("#awr-results")
        elif btn_id == "btn-copy-results":
            self.copy_all_text("#awr-results")

    def action_analyze(self) -> None:
        """Handler untuk hotkey Ctrl+Enter."""
        self.analyze_awr()

    def select_all_text(self, widget_id: str) -> None:
        """Memilih semua teks di TextArea."""
        text_area = self.query_one(widget_id, TextArea)
        text_area.focus()
        text_area.select_all()

    def copy_all_text(self, widget_id: str) -> None:
        """Menyalin semua teks dari TextArea ke clipboard."""
        text_area = self.query_one(widget_id, TextArea)
        text = text_area.text.strip()
        if text:
            self.app.copy_to_clipboard(text)
            self.notify("Results copied to clipboard!", severity="information")
        else:
            self.notify("No results to copy.", severity="warning")

    @work(exclusive=True, thread=True)
    def analyze_awr(self) -> None:
        paths_input = self.query_one("#awr-paths", TextArea).text.strip()
        results_widget = self.query_one("#awr-results", TextArea)

        if not paths_input:
            self.app.call_from_thread(
                self.notify, "Tidak ada file path yang dimasukkan!", severity="error"
            )
            return

        if not self.client:
            self.app.call_from_thread(
                results_widget.load_text, "ERROR: GEMINI_API_KEY tidak ditemukan."
            )
            return

        file_paths = [p.strip() for p in paths_input.splitlines() if p.strip()]
        valid_paths = []
        missing_files = []

        for path in file_paths:
            if os.path.exists(path):
                valid_paths.append(path)
            else:
                missing_files.append(path)

        if missing_files:
            self.app.call_from_thread(
                self.notify,
                f"File tidak ditemukan: {', '.join(missing_files)}",
                severity="warning",
            )

        if not valid_paths:
            self.app.call_from_thread(
                results_widget.load_text,
                "ERROR: Tidak ada file AWR yang valid ditemukan.\n\nPastikan path file sudah benar.",
            )
            return

        self.app.call_from_thread(
            results_widget.load_text,
            f"Reading {len(valid_paths)} AWR file(s)...\n\nAnalyzing with AI, please wait...",
        )

        awr_contents = []
        for path in valid_paths:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    # Limit content to first 50K characters per file to avoid token limits
                    if len(content) > 50000:
                        content = (
                            content[:50000]
                            + "\n... [content truncated for token limit]"
                        )
                    awr_contents.append(
                        f"=== FILE: {os.path.basename(path)} ===\n{content}\n"
                    )
            except Exception as e:
                awr_contents.append(
                    f"=== FILE: {os.path.basename(path)} ===\nERROR reading file: {str(e)}\n"
                )

        combined_content = "\n".join(awr_contents)

        prompt = (
            "You are an Oracle Database Performance Expert. Analyze the following AWR (Automatic Workload Repository) "
            "reports and provide a clear, easy-to-understand summary for non-technical people. "
            "Structure your analysis with these sections:\n\n"
            "1. DATABASE SERVER CONDITION:\n"
            "   - Overall health status\n"
            "   - Key performance indicators\n\n"
            "2. RECOMMENDATIONS (Priority Order):\n"
            "   - Immediate actions needed\n"
            "   - Medium-term improvements\n\n"
            "3. IO INFORMATION:\n"
            "   - Disk performance issues\n"
            "   - Read/Write metrics\n\n"
            "4. CPU INFORMATION:\n"
            "   - CPU usage patterns\n"
            "   - Top wait events\n\n"
            "5. MEMORY INFORMATION:\n"
            "   - SGA/PGA usage\n"
            "   - Memory bottlenecks\n\n"
            "6. Slow Query\n"
            "Use simple language. Avoid technical jargon where possible. If certain data is missing from the AWR, "
            "mention it and suggest what additional information would be helpful.\n\n"
            f"AWR Reports Content:\n{combined_content}"
        )

        try:
            self.app.call_from_thread(
                results_widget.load_text,
                "Analyzing AWR reports with AI... This may take a moment.",
            )

            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            result_text = (
                response.text.strip()
                if response.text
                else "No analysis returned from AI."
            )

            self.app.call_from_thread(results_widget.load_text, result_text)
            self.app.call_from_thread(
                self.notify, "AWR analysis completed!", severity="information"
            )

        except Exception as e:
            error_msg = f"Error during analysis: {str(e)}\n\nPlease check your API key and try again."
            self.app.call_from_thread(results_widget.load_text, error_msg)
            self.app.call_from_thread(self.notify, "Analysis failed.", severity="error")
