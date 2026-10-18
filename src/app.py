"""
app.py - the customtkinter GUI.  Run with:  python app.py

    pip install customtkinter send2trash

Concepts worth studying in this file:
  * Widgets are objects; layout is done with .pack() / .grid()
  * A GUI has ONE main thread running an event loop (mainloop). Long work
    must go in another thread or the window freezes.
  * Threads must not touch widgets directly, so the worker hands its
    result over through a queue that the main thread polls.
  * tkinter variables (BooleanVar) are "live" values bound to a widget.
"""

import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from deleter import delete_files
from scanner import DuplicateGroup, find_duplicates

MAX_GROUPS_SHOWN = 300  # building thousands of widgets is slow; see "Next steps"


def human_size(num_bytes: float) -> str:
    """1536 -> '1.5 KB'"""
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


class App(ctk.CTk):  # CTk is the main window; we subclass it to build on top
    def __init__(self):
        super().__init__()
        self.title("Duplicate File Finder")
        self.geometry("950x680")

        # ---- application state -------------------------------------------
        self.folder: str | None = None
        self.groups: list[DuplicateGroup] = []
        self.check_vars: dict[Path, ctk.BooleanVar] = {}   # path -> checkbox state
        self.result_queue: queue.Queue = queue.Queue()      # worker -> GUI messages

        self._build_ui()

    # ------------------------------------------------------------------
    # Building the interface
    # ------------------------------------------------------------------
    def _build_ui(self):
        # --- top bar: folder picker + options + scan button ---
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkButton(top, text="Choose folder...", command=self.choose_folder).pack(
            side="left", padx=8, pady=8
        )
        self.folder_label = ctk.CTkLabel(top, text="No folder selected", anchor="w")
        self.folder_label.pack(side="left", padx=8, fill="x", expand=True)

        self.same_folder_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(top, text="Same folder only", variable=self.same_folder_var).pack(
            side="left", padx=8
        )

        self.scan_button = ctk.CTkButton(top, text="Scan", command=self.start_scan, state="disabled")
        self.scan_button.pack(side="left", padx=8)

        # --- status line ---
        self.status_label = ctk.CTkLabel(self, text="Pick a folder to begin.", anchor="w")
        self.status_label.pack(fill="x", padx=20)

        # --- results area: a scrollable container we fill with groups later ---
        self.results = ctk.CTkScrollableFrame(self, label_text="Duplicate groups")
        self.results.pack(fill="both", expand=True, padx=12, pady=6)

        # --- bottom bar: selection count + delete button ---
        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=12, pady=(6, 12))

        self.selected_label = ctk.CTkLabel(bottom, text="0 files selected")
        self.selected_label.pack(side="left", padx=12, pady=8)

        self.delete_button = ctk.CTkButton(
            bottom,
            text="Delete selected",
            fg_color="#b3261e",
            hover_color="#8c1d18",
            command=self.delete_selected,
            state="disabled",
        )
        self.delete_button.pack(side="right", padx=12, pady=8)

    # ------------------------------------------------------------------
    # Choosing a folder
    # ------------------------------------------------------------------
    def choose_folder(self):
        folder = filedialog.askdirectory(title="Choose a folder to scan")
        if folder:  # empty string means the user cancelled
            self.folder = folder
            self.folder_label.configure(text=folder)
            self.scan_button.configure(state="normal")

    # ------------------------------------------------------------------
    # Scanning (in a background thread)
    # ------------------------------------------------------------------
    def start_scan(self):
        self.scan_button.configure(state="disabled")
        self.status_label.configure(text="Scanning... (this can take a while on big folders)")

        # Read the checkbox HERE, on the main thread, then pass the plain
        # bool to the worker. Workers shouldn't touch widgets or tk vars.
        same_folder = self.same_folder_var.get()

        threading.Thread(
            target=self._scan_worker,
            args=(self.folder, same_folder),
            daemon=True,  # daemon threads die with the program instead of blocking exit
        ).start()

        self.after(100, self._poll_queue)  # "call this in 100 ms" - no blocking

    def _scan_worker(self, folder: str, same_folder: bool):
        """Runs in the background thread."""
        try:
            groups = find_duplicates(folder, same_folder_only=same_folder)
            self.result_queue.put(("ok", groups))
        except Exception as exc:  # noqa: BLE001
            self.result_queue.put(("error", str(exc)))

    def _poll_queue(self):
        """Runs on the main thread: check whether the worker has finished."""
        try:
            kind, payload = self.result_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_queue)  # not done yet, check again soon
            return

        self.scan_button.configure(state="normal")
        if kind == "error":
            self.status_label.configure(text="Scan failed.")
            messagebox.showerror("Scan failed", payload)
        else:
            self.groups = payload
            self._render_groups()

    # ------------------------------------------------------------------
    # Showing results
    # ------------------------------------------------------------------
    def _render_groups(self):
        # Wipe the old widgets before drawing new ones.
        for child in self.results.winfo_children():
            child.destroy()
        self.check_vars.clear()

        if not self.groups:
            self.status_label.configure(text="No duplicates found. 🎉")
            self._update_selection_count()
            return

        shown = self.groups[:MAX_GROUPS_SHOWN]
        note = f" (showing first {MAX_GROUPS_SHOWN})" if len(self.groups) > MAX_GROUPS_SHOWN else ""
        self.status_label.configure(text=f"Found {len(self.groups)} duplicate groups{note}.")

        for group in shown:
            card = ctk.CTkFrame(self.results)
            card.pack(fill="x", padx=4, pady=5)

            ctk.CTkLabel(
                card,
                text=f"{group.name}   [{group.category}]",
                font=ctk.CTkFont(weight="bold"),
                anchor="w",
            ).pack(fill="x", padx=10, pady=(8, 2))

            for file in group.files:
                # Each checkbox owns a BooleanVar. Ticking the box changes the
                # var; reading the var tells us the state. That's the binding.
                var = ctk.BooleanVar(value=False)
                self.check_vars[file.path] = var

                ctk.CTkCheckBox(
                    card,
                    text=f"{file.path.name}   ({human_size(file.size)})   {file.path.parent}",
                    variable=var,
                    command=self._update_selection_count,  # fires on every click
                ).pack(anchor="w", padx=20, pady=2)

            ctk.CTkLabel(card, text="").pack(pady=2)  # bottom padding

        self._update_selection_count()

    def _selected_paths(self) -> list[Path]:
        return [path for path, var in self.check_vars.items() if var.get()]

    def _update_selection_count(self):
        count = len(self._selected_paths())
        self.selected_label.configure(text=f"{count} file{'s' if count != 1 else ''} selected")
        self.delete_button.configure(state="normal" if count else "disabled")

    # ------------------------------------------------------------------
    # Deleting
    # ------------------------------------------------------------------
    def delete_selected(self):
        selected = self._selected_paths()
        if not selected:
            return

        # Safety net: warn if the user ticked EVERY file in some group,
        # because that would erase the item completely.
        wiped = [
            g.name for g in self.groups[:MAX_GROUPS_SHOWN]
            if all(f.path in selected for f in g.files)
        ]
        if wiped:
            preview = ", ".join(wiped[:5]) + ("..." if len(wiped) > 5 else "")
            if not messagebox.askyesno(
                "Heads up",
                f"You selected ALL copies in {len(wiped)} group(s):\n{preview}\n\n"
                "Nothing would be left of them. Continue anyway?",
            ):
                return

        if not messagebox.askyesno(
            "Confirm delete", f"Move {len(selected)} file(s) to the Recycle Bin / Trash?"
        ):
            return

        deleted, failed = delete_files(selected)

        # Update our in-memory data instead of rescanning the disk.
        deleted_set = set(deleted)
        for group in self.groups:
            group.files = [f for f in group.files if f.path not in deleted_set]
        self.groups = [g for g in self.groups if len(g.files) > 1]  # singles aren't duplicates
        self._render_groups()

        msg = f"Moved {len(deleted)} file(s) to the trash."
        if failed:
            msg += f"\n\n{len(failed)} could not be deleted:\n" + "\n".join(
                f"{p.name}: {err}" for p, err in failed[:5]
            )
        messagebox.showinfo("Done", msg)


if __name__ == "__main__":
    ctk.set_appearance_mode("system")  # "light", "dark" or "system"
    ctk.set_default_color_theme("blue")
    App().mainloop()  # starts the event loop; blocks until the window closes