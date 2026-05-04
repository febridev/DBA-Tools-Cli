import json
import os

import requests
from dotenv import load_dotenv
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static, TextArea


class AWRAnalyzerScreen(Screen):
    """Screen for AWR Oracle analysis using AI."""

    CSS_PATH = "../styles.tcss"

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+enter", "analyze", "Analyze"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        load_dotenv(override=True)

        # Load configuration from .env
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()

        # Load 9router URL, use default localhost:8000 if not set in .env
        self.router_url = os.environ.get("ROUTER_URL", "http://127.0.0.1:8000").strip()
        # Ensure we use the full path if provided in .env
        if "\n" in self.router_url:
            urls = [u.strip() for u in self.router_url.split("\n") if u.strip()]
            # Prefer the one with /v1/ or the last one (usually more specific)
            self.router_url = next((u for u in reversed(urls) if "/v1/" in u), urls[-1])

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
        """Handler for Ctrl+Enter hotkey."""
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
                self.notify, "No file path provided!", severity="error"
            )
            return

        if not self.api_key:
            self.app.call_from_thread(
                results_widget.load_text, "ERROR: GEMINI_API_KEY not found."
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
                f"Files not found: {', '.join(missing_files)}",
                severity="warning",
            )

        if not valid_paths:
            self.app.call_from_thread(
                results_widget.load_text,
                "ERROR: No valid AWR files found.\n\nPlease check the file paths.",
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
                    # Limit content to first 30K characters to avoid proxy/token limits
                    if len(content) > 30000:
                        content = content[:30000] + "\n... [content truncated]"
                    awr_contents.append(
                        f"=== FILE: {os.path.basename(path)} ===\n{content}\n"
                    )
            except Exception as e:
                awr_contents.append(
                    f"=== FILE: {os.path.basename(path)} ===\nERROR reading file: {str(e)}\n"
                )

        combined_content = "\n".join(awr_contents)

        # Load prompt template from markdown file
        prompt_template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompts", "awr_analysis_prompt.md")
        try:
            with open(prompt_template_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            prompt = prompt_template.format(content=combined_content)
        except Exception as e:
            self.app.call_from_thread(self.notify, f"Error loading prompt template: {str(e)}", severity="error")
            # Fallback to simple prompt if file reading fails
            prompt = f"Analyze these AWR reports:\n{combined_content}"

        try:
            self.app.call_from_thread(
                results_widget.load_text,
                "Sending to 9Router... This may take a moment.",
            )

            # Match models from translator.py which are known to work
            available_models = [
                "gc/gemini-3-flash-preview",
                "anthropic/claude-3-opus",
                "openai/gpt-4-turbo",
            ]

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            result_text = None
            selected_model = None
            last_status = None
            last_error_msg = ""

            for model in available_models:
                payload = {
                    "model": model,
                    "stream": False,
                    "messages": [{"role": "user", "content": prompt}],
                }

                try:
                    response = requests.post(
                        self.router_url, headers=headers, json=payload, timeout=90
                    )
                    last_status = response.status_code
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("choices"):
                            result_text = (
                                data["choices"][0]
                                .get("message", {})
                                .get("content", "")
                                .strip()
                            )
                            if result_text:
                                selected_model = model
                                break
                    else:
                        last_error_msg = (
                            f"HTTP {response.status_code}: {response.text[:100]}"
                        )
                except Exception as e:
                    last_error_msg = str(e)
                    continue

            if not result_text:
                error_info = f"\n\nDetails: {last_error_msg if last_error_msg else 'No response from proxy'}"
                self.app.call_from_thread(
                    results_widget.load_text,
                    f"Error: All models failed or returned empty result.{error_info}",
                )
                self.app.call_from_thread(
                    self.notify, "Analysis failed.", severity="error"
                )
                return

            self.app.call_from_thread(results_widget.load_text, result_text)
            self.app.call_from_thread(
                self.notify,
                f"AWR analysis completed using {selected_model}!",
                severity="information",
            )

        except Exception as e:
            error_msg = f"Critical Error: {str(e)}\n\nPlease check your configuration."
            self.app.call_from_thread(results_widget.load_text, error_msg)
            self.app.call_from_thread(self.notify, "Analysis failed.", severity="error")
