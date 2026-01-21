# src/dba_tools/app.py

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Static, ListView, ListItem, Label
from textual.binding import Binding

# -- IMPORT NEW SCREEN -- 
from src.dba_tools.tui.screens.todo_list import ToDoListScreen 

# Konstanta Versi
APP_VERSION = "0.2.0"

ASCII_TITLE = r"""
╔╦╗╔╗ ╔═╗  ╔╦╗╔═╗╔═╗╦  ╔═╗
 ║║╠╩╗╠═╣   ║ ║ ║║ ║║  ╚═╗
═╩╝╚═╝╩ ╩   ╩ ╚═╝╚═╝╩═╝╚═╝
"""

class DBAToolsApp(App):
    """Aplikasi TUI Utama."""

    CSS_PATH = "tui/styles.tcss"
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "select_item", "Select", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="main-container"):
            
            # 1. HEADER
            with Container(id="header-area"):
                yield Static(ASCII_TITLE, classes="ascii-title")
                yield Static(APP_VERSION, classes="login-info")

            # 2. MENU LIST
            yield Label("[ SELECT_MODULE ]", classes="menu-label")
            
            yield ListView(
                ListItem(Label("1. \uf45e To-Do List"), id="opt-todolist"),
                ListItem(Label("2. \uebca SSH"), id="opt-ssh"),
                ListItem(Label("3. \ue706 DATABASE IDE"), id="opt-dbide"),
                ListItem(Label("4. \uf011 SYSTEM_EXIT"), id="opt-exit"),
                initial_index=0
            )

            # 3. FOOTER (Updated)
            # Menampilkan shortcut [Q] dan Versi Aplikasi
            footer_text = f"\[Q] QUIT_SYSTEM   |   BUILD_VER: {APP_VERSION}"
            yield Label(footer_text, classes="footer-text")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected_id = event.item.id
        
        if selected_id == "opt-todolist":
            # self.notify("ACCESSING To-Do List...", severity="information")
            self.push_screen(ToDoListScreen())
        elif selected_id == "opt-ssh":
            self.notify("ACCESSING SSH...", severity="information")
        elif selected_id == "opt-dbide":
            self.notify("ACCESSING Database IDE...", severity="information")
        elif selected_id == "opt-exit":
            self.exit()

def main():
    app = DBAToolsApp()
    app.run()

if __name__ == "__main__":
    main()
