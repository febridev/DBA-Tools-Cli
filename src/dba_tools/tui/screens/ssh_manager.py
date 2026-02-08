import os
import subprocess
import shlex
import platform
from pathlib import Path
from typing import List, Dict, Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, ListView, ListItem, Label, Input, Button
from textual.binding import Binding

# --- CUSTOM WIDGET FOR HOST ITEM ---
class SSHHostItem(ListItem):
    def __init__(self, host_name: str) -> None:
        self.host_name = host_name
        super().__init__(Label(host_name))


# --- HELPER CLASS FOR SSH CONFIG IO ---
class SSHConfigHelper:
    def __init__(self):
        self.config_path = Path.home() / ".ssh" / "config"
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        if not self.config_path.exists():
            self.config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.config_path.touch(mode=0o600)

    def get_all_hosts(self) -> List[str]:
        hosts = []
        if not self.config_path.exists():
            return hosts
            
        with open(self.config_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("Host ") and not line.startswith("Host *"):
                    parts = line.split()
                    if len(parts) > 1:
                        hosts.append(parts[1])
        return hosts

    def get_host_details(self, host_name: str) -> Dict[str, str]:
        details = {"Host": host_name, "HostName": "", "User": "", "Port": "22"}
        in_target_host = False
        
        with open(self.config_path, "r") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("Host "):
                    current_host = stripped.split()[1]
                    in_target_host = (current_host == host_name)
                
                if in_target_host:
                    if stripped.lower().startswith("hostname "):
                        details["HostName"] = stripped.split(maxsplit=1)[1]
                    elif stripped.lower().startswith("user "):
                        details["User"] = stripped.split(maxsplit=1)[1]
                    elif stripped.lower().startswith("port "):
                        details["Port"] = stripped.split(maxsplit=1)[1]
        return details

    def save_host_config(self, original_host: Optional[str], new_data: Dict[str, str]) -> bool:
        new_block = (
            f"Host {new_data['Host']}\n"
            f"    HostName {new_data['HostName']}\n"
            f"    User {new_data['User']}\n"
            f"    Port {new_data['Port']}\n"
        )
        try:
            if not original_host:
                with open(self.config_path, "a") as f:
                    f.write("\n" + new_block)
                return True

            with open(self.config_path, "r") as f:
                lines = f.readlines()

            new_lines = []
            skipping = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("Host "):
                    parts = stripped.split()
                    if len(parts) > 1:
                        if parts[1] == original_host:
                            skipping = True
                            new_lines.append(new_block) 
                        else:
                            skipping = False
                
                if not skipping:
                    new_lines.append(line)
            
            with open(self.config_path, "w") as f:
                f.writelines(new_lines)
            return True
        except Exception:
            return False


# --- UI SCREEN ---

class SSHManagerScreen(Screen):
    CSS_PATH = "../styles.tcss"
    BINDINGS = [
        Binding("escape", "handle_back", "Back"),
        Binding("down", "focus_list", "Focus List", show=False), 
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ssh_helper = SSHConfigHelper()
        self.editing_host: Optional[str] = None 
        self.connect_mode: bool = False
        self.all_hosts_cache: List[str] = []

    def compose(self) -> ComposeResult:
        with Container(id="main-container"):
            yield Static("[ MODULE: SSH_MANAGER ]", classes="header-area ascii-title")
            
            # --- 1. MAIN MENU ---
            with Vertical(id="ssh-menu-area"):
                yield Label("SELECT_ACTION:", classes="menu-label")
                yield ListView(
                    ListItem(Label("1. \uf0fe ADD_NEW_CONFIG"), id="opt-add"),
                    ListItem(Label("2. \uf044 EDIT_CONFIG"), id="opt-edit"),
                    ListItem(Label("3. \uf0c1 CONNECT_SSH (NEW TAB)"), id="opt-connect"),
                    id="ssh-main-list"
                )

            # --- 2. HOST SELECTION LIST ---
            with Vertical(id="ssh-host-list-area", classes="hidden"):
                yield Label(id="host-list-title", classes="menu-label")
                yield Input(placeholder="Type to search host...", id="search-box")
                yield Label("AVAILABLE_HOSTS:", classes="menu-label")
                yield ListView(id="host-list-view")
                yield Button("BACK", id="btn-back-to-menu")

            # --- 3. FORM INPUT ---
            with Vertical(id="ssh-form-area", classes="hidden"):
                yield Label("--- SSH CONFIGURATION FORM ---", classes="menu-label", id="form-title")
                yield Label("Host Alias:")
                yield Input(placeholder="e.g. MyServer", id="input-host")
                yield Label("HostName (IP/Domain):")
                yield Input(placeholder="e.g. 192.168.1.10", id="input-hostname")
                yield Label("User:")
                yield Input(placeholder="e.g. root", id="input-user")
                yield Label("Port:")
                yield Input(placeholder="22", value="22", id="input-port")
                
                with Horizontal(classes="button-row"):
                    yield Button("SAVE", id="btn-save-ssh")
                    yield Button("CANCEL", id="btn-cancel-ssh")

            yield Label("\[ESC] BACK | \[ENTER] SELECT", classes="footer-text")

    # --- ACTION HANDLERS ---

    def action_handle_back(self) -> None:
        if not self.query_one("#ssh-form-area").has_class("hidden"):
            if self.editing_host:
                self.query_one("#ssh-form-area").add_class("hidden")
                self.query_one("#ssh-host-list-area").remove_class("hidden")
                self.query_one("#search-box").focus()
            else:
                self._reset_to_main_menu()
            return
        if not self.query_one("#ssh-host-list-area").has_class("hidden"):
            self._reset_to_main_menu()
            return
        self.app.pop_screen()

    def action_focus_list(self):
        if not self.query_one("#ssh-host-list-area").has_class("hidden"):
            self.query_one("#host-list-view").focus()

    def _reset_to_main_menu(self):
        self.query_one("#ssh-menu-area").remove_class("hidden")
        self.query_one("#ssh-host-list-area").add_class("hidden")
        self.query_one("#ssh-form-area").add_class("hidden")
        self.editing_host = None
        self.connect_mode = False
        self.query_one("#ssh-main-list").focus()

    # --- EVENT HANDLERS ---

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-box":
            self.update_host_list(event.value.lower())

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-box":
            list_view = self.query_one("#host-list-view", ListView)
            if list_view.children:
                list_view.focus()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        list_id = event.list_view.id
        selected_id = event.item.id

        if list_id == "ssh-main-list":
            if selected_id == "opt-add":
                self.mode_add_new()
            elif selected_id == "opt-edit":
                self.connect_mode = False
                self.mode_select_host_list("SELECT HOST TO EDIT")
            elif selected_id == "opt-connect":
                self.connect_mode = True
                self.mode_select_host_list("SELECT HOST TO CONNECT")

        elif list_id == "host-list-view":
            if isinstance(event.item, SSHHostItem):
                if self.connect_mode:
                    self.launch_ssh_in_new_tab(event.item.host_name)
                else:
                    self.mode_edit_form(event.item.host_name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-cancel-ssh" or btn_id == "btn-back-to-menu":
            self.action_handle_back()
        elif btn_id == "btn-save-ssh":
            self.save_data()

    # --- LOGIC & HELPERS ---

    def mode_select_host_list(self, title: str):
        self.all_hosts_cache = self.ssh_helper.get_all_hosts()
        if not self.all_hosts_cache:
            self.notify("No SSH configurations found!", severity="error")
            return

        self.query_one("#host-list-title", Label).update(title)
        self.update_host_list(query="")
        self.query_one("#ssh-menu-area").add_class("hidden")
        self.query_one("#ssh-host-list-area").remove_class("hidden")
        
        search_input = self.query_one("#search-box", Input)
        search_input.value = "" 
        search_input.focus()

    def update_host_list(self, query: str = ""):
        list_view = self.query_one("#host-list-view", ListView)
        list_view.clear()
        filtered_hosts = [h for h in self.all_hosts_cache if query in h.lower()]
        for host in filtered_hosts:
            list_view.append(SSHHostItem(host))

    # --- NEW: LAUNCHER LOGIC ---
    # --- FIX: LAUNCHER LOGIC ---
    
    def launch_ssh_in_new_tab(self, host_alias: str):
        """
        Detects the OS/Terminal and launches SSH in a new tab/window.
        Does NOT suspend the TUI.
        """
        self.notify(f"Launching SSH for {host_alias}...", severity="information")

        system_os = platform.system()
        # Ambil full path untuk ssh agar lebih aman
        ssh_cmd = "ssh" 
        
        # Deteksi Terminal Emulator
        term_program = os.environ.get("TERM_PROGRAM", "").lower()
        
        try:
            # 1. WINDOWS TERMINAL (wt.exe)
            if system_os == "Windows":
                subprocess.Popen(f"wt -w 0 nt ssh {host_alias}", shell=True)
                return

            # 2. MACOS - iTerm2
            if "iterm" in term_program:
                script = f'''
                tell application "iTerm"
                    tell current window
                        create tab with default profile
                        tell current session of current tab
                            write text "{ssh_cmd} {host_alias}"
                        end tell
                    end tell
                end tell
                '''
                subprocess.run(["osascript", "-e", script])
                return

            # 3. MACOS/LINUX - Ghostty 
            # FIX: Argumen dipisah koma dalam list, jangan digabung string f""
            if "ghostty" in term_program:
                subprocess.Popen(["ghostty", "-e", ssh_cmd, host_alias])
                return

            # 4. MACOS - Default Terminal.app
            if system_os == "Darwin" and "apple_terminal" in term_program:
                script = f'''
                tell application "Terminal"
                    do script "{ssh_cmd} {host_alias}"
                    activate
                end tell
                '''
                subprocess.run(["osascript", "-e", script])
                return

            # 5. LINUX - Gnome Terminal (Ubuntu Default)
            if system_os == "Linux":
                if os.path.exists("/usr/bin/gnome-terminal"):
                    subprocess.Popen(["gnome-terminal", "--tab", "--", ssh_cmd, host_alias])
                    return
                # Fallback: x-terminal-emulator
                subprocess.Popen(["x-terminal-emulator", "-e", f"{ssh_cmd} {host_alias}"])
                return

            # 6. Fallback Generic (Mencoba membuka window baru default system)
            # Jika terminal tidak terdeteksi, kita coba jalankan command langsung
            self.notify("Terminal type not detected explicitly. Trying generic launch.", severity="warning")
            if system_os == "Darwin":
                 subprocess.Popen(["open", "-a", "Terminal", f"ssh {host_alias}"]) # Fallback Mac
            else:
                 subprocess.Popen(["x-terminal-emulator", "-e", f"ssh {host_alias}"])

        except Exception as e:
            self.notify(f"Failed to launch terminal: {e}", severity="error")
    

    def mode_add_new(self):
        self.editing_host = None
        self.query_one("#form-title", Label).update("--- ADD NEW SSH CONFIG ---")
        self.query_one("#ssh-menu-area").add_class("hidden")
        self.query_one("#ssh-form-area").remove_class("hidden")
        self.query_one("#input-host").focus()

    def mode_edit_form(self, host_name: str):
        self.editing_host = host_name
        self.query_one("#form-title", Label).update(f"--- EDITING: {host_name} ---")
        
        data = self.ssh_helper.get_host_details(host_name)
        self.query_one("#input-host").value = data.get("Host", "")
        self.query_one("#input-hostname").value = data.get("HostName", "")
        self.query_one("#input-user").value = data.get("User", "")
        self.query_one("#input-port").value = data.get("Port", "22")

        self.query_one("#ssh-host-list-area").add_class("hidden")
        self.query_one("#ssh-form-area").remove_class("hidden")
        self.query_one("#input-hostname").focus()

    def save_data(self):
        host = self.query_one("#input-host").value.strip()
        hostname = self.query_one("#input-hostname").value.strip()
        user = self.query_one("#input-user").value.strip()
        port = self.query_one("#input-port").value.strip()

        if not all([host, hostname, user]):
            self.notify("Host, Hostname, and User are required!", severity="error")
            return

        new_data = {"Host": host, "HostName": hostname, "User": user, "Port": port}
        success = self.ssh_helper.save_host_config(self.editing_host, new_data)
        
        if success:
            msg = "Config Updated!" if self.editing_host else "Config Added!"
            self.notify(msg, severity="information")
            self._reset_to_main_menu()
        else:
            self.notify("Failed to save configuration.", severity="error")
