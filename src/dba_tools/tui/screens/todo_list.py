import json
from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container
from textual.widgets import Static, ListView, ListItem, Label, Input
from textual.binding import Binding

# Lokasi File Penyimpanan (di root folder project)
DATA_FILE = Path("todo_data.json")

class ToDoListScreen(Screen):
    """Screen interaktif untuk To-Do List dengan Auto-Save (JSON)."""

    CSS_PATH = "../styles.tcss"

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("delete", "delete_task", "Delete Task"),
        Binding("space", "toggle_task", "Mark Done/Undone"),
    ]
    
    def _make_todo_item(self, text: str, done: bool = False) -> ListItem:
        """Helper untuk membuat ListItem dengan metadata."""
        mark = "x" if done else " "
        display_text = f"[{mark}] {text.upper()}"
        
        label = Label(display_text)
        label.raw_text = text.upper() # Simpan state teks asli
        
        item = ListItem(label)
        if done:
            item.add_class("task-done")
            
        return item

    def compose(self) -> ComposeResult:
        """Menyusun layout UI."""
        with Container(id="main-container"):
            yield Static("[ MODULE: TO_DO_LIST ]", classes="header-area ascii-title")
            
            yield Label("NEW_TASK_ENTRY:", classes="menu-label")
            yield Input(placeholder="Type task & press Enter...", id="task-input")

            yield Label("ACTIVE_TASKS:", classes="menu-label", id="list-label")
            
            # Kita mulai dengan List kosong, nanti diisi oleh on_mount
            yield ListView(id="todo-list")
            
            yield Label("\[ESC] BACK | \[SPACE] TOGGLE | \[DEL] REMOVE", classes="footer-text")

    def on_mount(self) -> None:
        """Event yang berjalan otomatis saat Screen muncul."""
        self.load_todos()
    def save_todos(self) -> None:
        """Menyimpan seluruh state list ke file JSON."""
        todo_list = self.query_one("#todo-list", ListView)
        data = []

        # Loop semua item di layar
        for item in todo_list.children:
            if isinstance(item, ListItem):
                # --- PERBAIKAN DI SINI ---
                # Jangan gunakan query_one() karena bisa error pada item yang baru ditambahkan (belum mounted).
                # Kita cari child yang bertipe Label secara manual dari list children.
                label = None
                for child in item.children:
                    if isinstance(child, Label):
                        label = child
                        break
                
                # Hanya simpan jika Label ditemukan
                if label:
                    is_done = item.has_class("task-done")
                    
                    # Ambil text, fallback jika raw_text hilang
                    text = getattr(label, "raw_text", "UNKNOWN")
                    
                    data.append({
                        "task": text,
                        "done": is_done
                    })
        
        # Tulis ke file
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            self.notify(f"ERROR SAVING DATA: {e}", severity="error")

    def load_todos(self) -> None:
        """Membaca file JSON dan merender ulang list."""
        if not DATA_FILE.exists():
            # Jika file belum ada, buat file dummy/default
            default_data = [
                {"task": "INSTALL_DBA_TOOLS", "done": True},
                {"task": "CONFIGURE_ENV", "done": False}
            ]
            with open(DATA_FILE, "w") as f:
                json.dump(default_data, f, indent=4)
        
        # Baca File
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                
            todo_list = self.query_one("#todo-list", ListView)
            todo_list.clear() # Bersihkan list lama
            
            for entry in data:
                new_item = self._make_todo_item(entry["task"], entry["done"])
                todo_list.append(new_item)
                
        except Exception as e:
            self.notify(f"ERROR LOADING DATA: {e}", severity="error")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handler tambah tugas baru."""
        task_text = event.value.strip()
        
        if task_text:
            todo_list = self.query_one("#todo-list", ListView)
            new_item = self._make_todo_item(task_text)
            todo_list.append(new_item)
            event.input.value = ""
            self.notify("TASK_ADDED_SUCCESSFULLY")
            
            # AUTO SAVE
            self.save_todos()

    def action_delete_task(self) -> None:
        """Handler hapus tugas."""
        todo_list = self.query_one("#todo-list", ListView)
        selected_item = todo_list.highlighted_child
        
        if selected_item:
            selected_item.remove()
            self.notify("TASK_REMOVED", severity="warning")
            
            # AUTO SAVE
            self.save_todos()

    def action_toggle_task(self) -> None:
        """Handler toggle status tugas."""
        todo_list = self.query_one("#todo-list", ListView)
        
        if todo_list.highlighted_child:
            item = todo_list.highlighted_child
            label = item.query_one(Label) 
            
            # Recovery text jika perlu
            if not hasattr(label, "raw_text"):
                try:
                    current_display = str(label.renderable)
                    label.raw_text = current_display[4:] 
                except:
                    label.raw_text = "UNKNOWN_TASK"

            text = label.raw_text
            
            if item.has_class("task-done"):
                item.remove_class("task-done")
                label.update(f"[ ] {text}")
            else:
                item.add_class("task-done")
                label.update(f"[x] {text}")
            
            # AUTO SAVE
            self.save_todos()
