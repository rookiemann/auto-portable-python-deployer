"""
Auto Portable Python Deployer - Tkinter GUI Application

Generates self-contained portable Python deployment packages.
"""
import os
import sys
from pathlib import Path

# Bootstrap: ensure project root is on sys.path
_BASE_DIR = Path(__file__).parent.resolve()
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading

from config import BASE_DIR, WINDOW_TITLE, WINDOW_SIZE, APP_VERSION
from core.python_manager import PYTHON_VERSIONS, PYTHON_VERSION_LABELS
from core.package_generator import PackageConfig, PackageGenerator


class DeployerApp:
    """Main GUI application for the Portable Python Deployer."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{WINDOW_TITLE} v{APP_VERSION}")
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(800, 650)

        # Theme
        self.style = ttk.Style()
        available = self.style.theme_names()
        for theme in ("vista", "winnative", "clam", "default"):
            if theme in available:
                self.style.theme_use(theme)
                break

        self.style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        self.style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        self.style.configure("Generate.TButton", font=("Segoe UI", 11, "bold"))
        self.style.configure("Status.TLabel", font=("Segoe UI", 9))

        # Variables
        self.project_name_var = tk.StringVar(value="MyProject")
        self.output_dir_var = tk.StringVar(value=str(BASE_DIR / "output"))
        self.python_version_var = tk.StringVar(value="3.12")
        self.entry_point_var = tk.StringVar(value="app.py")
        self.launcher_name_var = tk.StringVar(value="launcher.bat")
        self.include_git_var = tk.BooleanVar(value=False)
        self.include_ffmpeg_var = tk.BooleanVar(value=False)
        self.include_tkinter_var = tk.BooleanVar(value=True)
        self.extra_pth_var = tk.StringVar(value="")
        self.extra_pip_args_var = tk.StringVar(value="")

        self._generating = False

        self._build_ui()

    def _build_ui(self):
        """Build the main UI layout."""
        # Main container with padding
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(main, text="Auto Portable Python Deployer",
                          style="Title.TLabel")
        title.pack(pady=(0, 10))

        # Create a paned window: top for config, bottom for log
        paned = ttk.PanedWindow(main, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Top section: config panels
        config_frame = ttk.Frame(paned)
        paned.add(config_frame, weight=3)

        # Bottom section: log output
        log_frame = ttk.Frame(paned)
        paned.add(log_frame, weight=2)

        # Build config panels in a 2-column layout
        left_col = ttk.Frame(config_frame)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        right_col = ttk.Frame(config_frame)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self._build_project_panel(left_col)
        self._build_options_panel(left_col)
        self._build_dependencies_panel(right_col)
        self._build_generation_panel(right_col)
        self._build_log_panel(log_frame)

    def _build_project_panel(self, parent):
        """Project configuration panel."""
        frame = ttk.LabelFrame(parent, text=" Project Configuration ",
                               style="Section.TLabelframe", padding=8)
        frame.pack(fill=tk.X, pady=(0, 5))

        # Project Name
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Project Name:", width=16, anchor="w").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.project_name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Output Directory
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Output Directory:", width=16, anchor="w").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.output_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(row, text="Browse...", width=10,
                   command=self._browse_output_dir).pack(side=tk.RIGHT)

        # Python Version
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Python Version:", width=16, anchor="w").pack(side=tk.LEFT)

        version_labels = list(PYTHON_VERSION_LABELS.values())
        version_keys = list(PYTHON_VERSION_LABELS.keys())
        self._version_combo = ttk.Combobox(row, values=version_labels, state="readonly", width=50)
        # Default to 3.12
        default_idx = version_keys.index("3.12") if "3.12" in version_keys else 0
        self._version_combo.current(default_idx)
        self._version_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._version_combo.bind("<<ComboboxSelected>>", self._on_version_change)
        self._version_keys = version_keys

        # Entry Point
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Entry Point:", width=16, anchor="w").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.entry_point_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Launcher Name
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Launcher Name:", width=16, anchor="w").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.launcher_name_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_options_panel(self, parent):
        """Options panel with checkboxes."""
        frame = ttk.LabelFrame(parent, text=" Portable Components ",
                               style="Section.TLabelframe", padding=8)
        frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Checkbutton(frame, text="Include Tkinter (GUI framework)",
                        variable=self.include_tkinter_var).pack(anchor="w", pady=1)
        ttk.Checkbutton(frame, text="Include Portable Git (for git clone operations)",
                        variable=self.include_git_var).pack(anchor="w", pady=1)
        ttk.Checkbutton(frame, text="Include Portable FFmpeg (for audio/video processing)",
                        variable=self.include_ffmpeg_var).pack(anchor="w", pady=1)

        # Extra ._pth paths
        sep = ttk.Separator(frame, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, pady=5)

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Extra ._pth paths:", width=16, anchor="w").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.extra_pth_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tip = ttk.Label(frame, text="Comma-separated relative paths added to Python path (e.g., ..\\mylib,src)",
                        font=("Segoe UI", 8), foreground="gray")
        tip.pack(anchor="w")

        # Extra pip args
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Extra pip args:", width=16, anchor="w").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.extra_pip_args_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tip2 = ttk.Label(frame, text="Extra pip install arguments (e.g., --index-url https://...)",
                         font=("Segoe UI", 8), foreground="gray")
        tip2.pack(anchor="w")

    def _build_dependencies_panel(self, parent):
        """Dependencies panel with text area."""
        frame = ttk.LabelFrame(parent, text=" Requirements (requirements.txt) ",
                               style="Section.TLabelframe", padding=8)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Toolbar
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, pady=(0, 3))
        ttk.Button(toolbar, text="Load File...", command=self._load_requirements).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="Clear", command=self._clear_requirements).pack(side=tk.LEFT)

        # Text area
        self.req_text = scrolledtext.ScrolledText(frame, height=8, width=40,
                                                  font=("Consolas", 10),
                                                  wrap=tk.NONE)
        self.req_text.pack(fill=tk.BOTH, expand=True)
        self.req_text.insert("1.0", "# Add your pip dependencies here, one per line\n"
                                    "# Example:\n"
                                    "# requests>=2.31.0\n"
                                    "# flask\n"
                                    "# numpy\n")

    def _build_generation_panel(self, parent):
        """Generation controls."""
        frame = ttk.LabelFrame(parent, text=" Generate Package ",
                               style="Section.TLabelframe", padding=8)
        frame.pack(fill=tk.X, pady=(0, 5))

        # Progress bar
        self.progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progress.pack(fill=tk.X, pady=(0, 5))

        # Status label
        self.status_label = ttk.Label(frame, text="Ready to generate.",
                                      style="Status.TLabel")
        self.status_label.pack(fill=tk.X, pady=(0, 5))

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        self.generate_btn = ttk.Button(btn_frame, text="Generate Deployment Package",
                                       style="Generate.TButton",
                                       command=self._on_generate)
        self.generate_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.open_btn = ttk.Button(btn_frame, text="Open Output", state="disabled",
                                   command=self._open_output)
        self.open_btn.pack(side=tk.RIGHT)

    def _build_log_panel(self, parent):
        """Log output panel."""
        frame = ttk.LabelFrame(parent, text=" Log Output ",
                               style="Section.TLabelframe", padding=5)
        frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.log_text = scrolledtext.ScrolledText(frame, height=6,
                                                  font=("Consolas", 9),
                                                  state="disabled",
                                                  wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    # ---- Event Handlers ----

    def _on_version_change(self, event=None):
        """Update internal version when combo changes."""
        idx = self._version_combo.current()
        if 0 <= idx < len(self._version_keys):
            self.python_version_var.set(self._version_keys[idx])

    def _browse_output_dir(self):
        d = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if d:
            self.output_dir_var.set(d)

    def _load_requirements(self):
        f = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Load requirements.txt"
        )
        if f:
            try:
                content = Path(f).read_text(encoding="utf-8")
                self.req_text.delete("1.0", tk.END)
                self.req_text.insert("1.0", content)
                self._log(f"Loaded requirements from: {f}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{e}")

    def _clear_requirements(self):
        self.req_text.delete("1.0", tk.END)

    def _open_output(self):
        output_dir = Path(self.output_dir_var.get()) / self.project_name_var.get().replace(" ", "_")
        if output_dir.exists():
            os.startfile(str(output_dir))
        else:
            messagebox.showinfo("Info", "Output directory doesn't exist yet.")

    def _log(self, message: str):
        """Append message to the log panel (thread-safe)."""
        def _do():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.root.after(0, _do)

    def _update_progress(self, current: int, total: int, message: str):
        """Update progress bar and status (thread-safe)."""
        def _do():
            pct = int(current / total * 100) if total > 0 else 0
            self.progress["value"] = pct
            self.status_label.config(text=message)
        self.root.after(0, _do)

    def _on_generate(self):
        """Start package generation in a background thread."""
        if self._generating:
            return

        # Validate inputs
        project_name = self.project_name_var.get().strip()
        if not project_name:
            messagebox.showwarning("Validation", "Please enter a project name.")
            return

        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            messagebox.showwarning("Validation", "Please select an output directory.")
            return

        entry_point = self.entry_point_var.get().strip()
        if not entry_point:
            messagebox.showwarning("Validation", "Please enter an entry point filename.")
            return

        # Get selected python version
        idx = self._version_combo.current()
        python_minor = self._version_keys[idx] if 0 <= idx < len(self._version_keys) else "3.12"

        # Parse extra pth paths
        extra_pth_raw = self.extra_pth_var.get().strip()
        extra_pth = [p.strip() for p in extra_pth_raw.split(",") if p.strip()] if extra_pth_raw else []

        # Get requirements
        requirements = self.req_text.get("1.0", tk.END).strip()
        # Filter out comment-only lines for display, but keep all for file
        req_lines = [l for l in requirements.split("\n") if l.strip() and not l.strip().startswith("#")]

        # Build config
        config = PackageConfig(
            project_name=project_name,
            python_minor=python_minor,
            output_dir=Path(output_dir),
            entry_point=entry_point,
            launcher_name=self.launcher_name_var.get().strip() or "launcher.bat",
            requirements=requirements,
            include_git=self.include_git_var.get(),
            include_ffmpeg=self.include_ffmpeg_var.get(),
            include_tkinter=self.include_tkinter_var.get(),
            extra_pth_paths=extra_pth,
            extra_pip_args=self.extra_pip_args_var.get().strip(),
        )

        # Log configuration summary
        self._log("=" * 50)
        self._log(f"Generating deployment package: {project_name}")
        self._log(f"  Python: {PYTHON_VERSIONS.get(python_minor, '?')} ({python_minor})")
        self._log(f"  Entry point: {entry_point}")
        self._log(f"  Output: {output_dir}/{project_name.replace(' ', '_')}")
        self._log(f"  Tkinter: {'Yes' if config.include_tkinter else 'No'}")
        self._log(f"  Git: {'Yes' if config.include_git else 'No'}")
        self._log(f"  FFmpeg: {'Yes' if config.include_ffmpeg else 'No'}")
        if req_lines:
            self._log(f"  Requirements: {len(req_lines)} package(s)")
        self._log("-" * 50)

        # Disable button, start generation
        self._generating = True
        self.generate_btn.config(state="disabled")
        self.open_btn.config(state="disabled")

        def _generate_thread():
            try:
                generator = PackageGenerator(config)

                def progress_cb(current, total, message):
                    self._update_progress(current, total, message)
                    self._log(f"  {message}")

                success = generator.generate(progress_callback=progress_cb)

                if success:
                    self._log("")
                    self._log("Package generated successfully!")
                    self._log(f"  Location: {generator.output_path}")
                    self._log("")
                    self._log("To deploy, run install.bat in the output folder.")
                    self.root.after(0, lambda: self.open_btn.config(state="normal"))
                else:
                    self._log("")
                    self._log("ERROR: Package generation failed.")

            except Exception as e:
                self._log(f"ERROR: {e}")
                import traceback
                self._log(traceback.format_exc())

            finally:
                self._generating = False
                self.root.after(0, lambda: self.generate_btn.config(state="normal"))

        thread = threading.Thread(target=_generate_thread, daemon=True)
        thread.start()


def main():
    # Check for CLI mode
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        from core.cli import run_cli
        sys.exit(run_cli(sys.argv[2:]))

    # GUI mode
    root = tk.Tk()

    try:
        root.iconbitmap(default="")
    except Exception:
        pass

    app = DeployerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
