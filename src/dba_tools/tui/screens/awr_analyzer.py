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
        Binding("f5", "analyze", "Analyze"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        load_dotenv(override=True)

        # Load configuration from .env (fallback to dummy key for routers that don't need auth)
        self.api_key = os.environ.get("ROUTER_API_KEY", os.environ.get("GEMINI_API_KEY", "dummy-router-key")).strip()

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
                    "Input AWR File/Directory Paths (one per line):", classes="menu-label"
                )

                yield TextArea(
                    id="awr-paths",
                    placeholder="Enter full paths to AWR files or directories (html/txt)...",
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

            yield Label("\[ESC] BACK | \[F5] or \[CTRL+ENTER] ANALYZE", classes="footer-text")

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


        import pathlib

        file_paths = [p.strip() for p in paths_input.splitlines() if p.strip()]
        valid_paths = []
        missing_inputs = []

        for path_str in file_paths:
            p = pathlib.Path(path_str)
            if not p.exists():
                missing_inputs.append(path_str)
            elif p.is_file():
                valid_paths.append(str(p))
            elif p.is_dir():
                for ext in ('*.html', '*.txt'):
                    for f in p.rglob(ext):
                        if f.is_file():
                            valid_paths.append(str(f))

        # Sort valid paths chronologically (based on filename)
        valid_paths = sorted(list(set(valid_paths)))

        if missing_inputs:
            self.app.call_from_thread(
                self.notify,
                f"Paths not found: {', '.join(missing_inputs)}",
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

        # Use a detailed internal prompt to guarantee HTML output focusing on CPU, Memory, IO, and Queries
        prompt = f"""You are an Expert Oracle Database Administrator.
I have provided {len(valid_paths)} Oracle AWR reports spanning different times. 
Please compare them and provide a comprehensive summary of the database performance trends and anomalies.

Specifically, I need you to focus on and detail the following aspects:
1. CPU Usage and Bottlenecks
2. Memory Allocation and Issues
3. I/O Performance and Wait Events
4. Top Queries (SQL ordered by Elapsed Time/CPU/Gets) and recommendations

CRITICAL INSTRUCTIONS:
- You MUST format your entire response as a valid, stylized HTML document.
- Do NOT use markdown code blocks (```html ... ```), output ONLY the raw HTML.
- Use a modern, clean CSS style (embedded in <style> tags).
- Include tables to compare metrics across the different time periods.
- **Time Context**: Whenever presenting data or metrics, clearly state the specific Date and Time (Snapshot Time) for each AWR report so we know exactly when the data is from.
- **Definitive Conclusion**: At the very end of your report, provide a highly visible 'Final Conclusion & DBA Action Plan' section. This section MUST explicitly conclude whether the Database is healthy ('DB is OK') or if it requires immediate action ('Needs DBA Action'), followed by a prioritized bulleted list of the exact actions the DBA should take.

AWR Data:
{combined_content}
"""

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

            # Clean up potential markdown wrappers
            if result_text.startswith("```html"):
                result_text = result_text[7:]
            elif result_text.startswith("```"):
                result_text = result_text[3:]
            
            if result_text.endswith("```"):
                result_text = result_text[:-3]
                
            result_text = result_text.strip()

            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"awr_summary_{timestamp}.html"
            report_path = os.path.abspath(report_filename)
            
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(result_text)
                
                success_msg = f"Analysis completed successfully!\n\nHTML Report saved to:\n{report_path}\n\nYou can open this file in your web browser."
                self.app.call_from_thread(results_widget.load_text, success_msg)
                self.app.call_from_thread(
                    self.notify,
                    f"Analysis completed! Saved to {report_filename}",
                    severity="information",
                )
            except Exception as io_err:
                self.app.call_from_thread(
                    results_widget.load_text, 
                    f"Analysis completed but failed to save file: {str(io_err)}\n\nRaw Output:\n{result_text}"
                )

        except Exception as e:
            error_msg = f"Critical Error: {str(e)}\n\nPlease check your configuration."
            self.app.call_from_thread(results_widget.load_text, error_msg)
            self.app.call_from_thread(self.notify, "Analysis failed.", severity="error")
