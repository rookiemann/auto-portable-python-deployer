"""
Python Embedded Distribution Manager

Downloads and configures Python embeddable distributions for Windows.
Supports Python 3.10 through 3.14.
"""
import os
import subprocess
import zipfile
from pathlib import Path
from typing import Optional, Callable

# Latest known patch versions with embeddable ZIP available on python.org
# (Security-only releases drop Windows embeddable builds)
PYTHON_VERSIONS = {
    "3.10": "3.10.11",
    "3.11": "3.11.9",
    "3.12": "3.12.10",
    "3.13": "3.13.12",
    "3.14": "3.14.3",
}

# Display labels for the GUI
PYTHON_VERSION_LABELS = {
    "3.10": "Python 3.10 (3.10.11) - Stable, wide compatibility",
    "3.11": "Python 3.11 (3.11.9) - Stable, faster",
    "3.12": "Python 3.12 (3.12.10) - Stable, recommended",
    "3.13": "Python 3.13 (3.13.12) - Stable, latest features",
    "3.14": "Python 3.14 (3.14.3) - Stable, newest",
}


def get_python_url(version: str) -> str:
    """Get the download URL for a Python embeddable ZIP."""
    return f"https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip"


def get_tkinter_url(version: str) -> str:
    """Get the download URL for the tcltk.msi component."""
    return f"https://www.python.org/ftp/python/{version}/amd64/tcltk.msi"


def get_pth_zip_name(minor_version: str) -> str:
    """Get the stdlib zip name for a Python version (e.g., 'python312.zip')."""
    parts = minor_version.split(".")
    return f"python{parts[0]}{parts[1]}.zip"


class PythonManager:
    """Manages embedded Python download, extraction, and configuration."""

    def __init__(self, base_dir: Path, python_version: str = "3.12.8"):
        self.base_dir = base_dir
        self.python_version = python_version
        self.minor_version = ".".join(python_version.split(".")[:2])
        self.python_dir = self.base_dir / "python_embedded"
        self.python_exe = self.python_dir / "python.exe"
        self.site_packages = self.python_dir / "Lib" / "site-packages"

    @property
    def is_installed(self) -> bool:
        return self.python_exe.exists() and self.site_packages.exists()

    @property
    def has_pip(self) -> bool:
        if not self.python_exe.exists():
            return False
        result = subprocess.run(
            [str(self.python_exe), "-m", "pip", "--version"],
            capture_output=True, text=True
        )
        return result.returncode == 0

    @property
    def pth_file(self) -> Optional[Path]:
        for f in self.python_dir.glob("python*._pth"):
            return f
        return None

    def download_and_setup(
        self,
        progress_callback: Optional[Callable] = None,
        extra_pth_paths: Optional[list] = None,
        setup_tkinter: bool = True,
    ) -> bool:
        """Download, extract, and configure embedded Python.

        Args:
            progress_callback: Optional callback(current, total, message)
            extra_pth_paths: Additional paths to add to ._pth file
            setup_tkinter: Whether to download and install tkinter

        Returns:
            True if setup completed successfully.
        """
        if self.is_installed and self.has_pip:
            if progress_callback:
                progress_callback(100, 100, "Embedded Python already installed")
            return True

        try:
            # Step 1: Download
            if not self.python_exe.exists():
                if progress_callback:
                    progress_callback(0, 100, f"Downloading Python {self.python_version}...")

                url = get_python_url(self.python_version)
                zip_path = self.base_dir / "python_embedded.zip"
                self._download_file(url, zip_path, progress_callback,
                                    label=f"Python {self.python_version}", pct_range=(5, 40))

                # Step 2: Extract
                if progress_callback:
                    progress_callback(42, 100, "Extracting Python...")

                self.python_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(self.python_dir)

                zip_path.unlink(missing_ok=True)

            # Step 3: Configure ._pth
            if progress_callback:
                progress_callback(50, 100, "Configuring Python paths...")

            self._configure_pth(extra_pth_paths)

            # Step 4: Create site-packages
            self.site_packages.mkdir(parents=True, exist_ok=True)

            # Step 5: Bootstrap pip
            if not self.has_pip:
                if progress_callback:
                    progress_callback(55, 100, "Bootstrapping pip...")
                self._bootstrap_pip(progress_callback)

            # Step 6: Set up tkinter
            if setup_tkinter:
                if progress_callback:
                    progress_callback(80, 100, "Setting up tkinter...")
                self._setup_tkinter(progress_callback)

            if progress_callback:
                progress_callback(100, 100, "Embedded Python ready")
            return True

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error setting up Python: {e}")
            return False

    def _download_file(
        self,
        url: str,
        dest: Path,
        progress_callback: Optional[Callable] = None,
        label: str = "file",
        pct_range: tuple = (5, 50),
    ):
        """Download a file with progress reporting using urllib."""
        import urllib.request
        import ssl

        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={
            "User-Agent": "PortablePythonDeployer/1.0"
        })

        with urllib.request.urlopen(req, context=ctx) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 65536
            pct_start, pct_end = pct_range

            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        pct = int(downloaded / total_size * (pct_end - pct_start)) + pct_start
                        mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        progress_callback(pct, 100, f"Downloading {label}... {mb:.1f}/{total_mb:.1f} MB")

    def _configure_pth(self, extra_paths: Optional[list] = None):
        """Configure the ._pth file to enable site-packages and import site."""
        pth = self.pth_file
        if pth is None:
            raise FileNotFoundError("Could not find python*._pth file in embedded Python")

        # Find the stdlib zip name
        zip_name = None
        for f in self.python_dir.glob("python*.zip"):
            zip_name = f.name
            break

        if zip_name is None:
            zip_name = get_pth_zip_name(self.minor_version)

        lines = [
            zip_name,
            ".",
            "Lib",
            "Lib\\site-packages",
            "DLLs",
        ]

        if extra_paths:
            lines.extend(extra_paths)

        lines.append("")
        lines.append("import site")

        pth.write_text("\n".join(lines), encoding="ascii")

    def _bootstrap_pip(self, progress_callback: Optional[Callable] = None):
        """Bootstrap pip by downloading get-pip.py."""
        import urllib.request
        import ssl

        get_pip_path = self.python_dir / "get-pip.py"

        if progress_callback:
            progress_callback(60, 100, "Downloading get-pip.py...")

        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            "https://bootstrap.pypa.io/get-pip.py",
            headers={"User-Agent": "PortablePythonDeployer/1.0"}
        )
        with urllib.request.urlopen(req, context=ctx) as response:
            get_pip_path.write_bytes(response.read())

        if progress_callback:
            progress_callback(65, 100, "Installing pip...")

        result = subprocess.run(
            [str(self.python_exe), str(get_pip_path)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"get-pip.py failed: {result.stderr}")

        get_pip_path.unlink(missing_ok=True)

        if progress_callback:
            progress_callback(75, 100, "Upgrading pip...")

        subprocess.run(
            [str(self.python_exe), "-m", "pip", "install", "--upgrade", "pip"],
            capture_output=True, text=True
        )

    def _setup_tkinter(self, progress_callback: Optional[Callable] = None) -> bool:
        """Download and install tkinter for embedded Python."""
        # Check if tkinter already works
        try:
            result = subprocess.run(
                [str(self.python_exe), "-c", "import _tkinter; print('ok')"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                if progress_callback:
                    progress_callback(95, 100, "tkinter already available")
                return True
        except Exception:
            pass

        if progress_callback:
            progress_callback(82, 100, "Downloading tkinter components...")

        msi_url = get_tkinter_url(self.python_version)
        msi_path = self.base_dir / "_tcltk.msi"
        extract_dir = self.base_dir / "_tcltk_extract"

        try:
            import shutil

            self._download_file(msi_url, msi_path, progress_callback,
                                label="tkinter", pct_range=(83, 88))

            if progress_callback:
                progress_callback(89, 100, "Extracting tkinter files...")

            if extract_dir.exists():
                shutil.rmtree(extract_dir)

            subprocess.run(
                ["msiexec", "/a", str(msi_path), "/qn",
                 f"TARGETDIR={extract_dir}"],
                capture_output=True, timeout=60
            )

            if progress_callback:
                progress_callback(92, 100, "Installing tkinter files...")

            # Copy DLLs next to python.exe
            dlls_dir = extract_dir / "DLLs"
            for name in ("_tkinter.pyd", "tcl86t.dll", "tk86t.dll", "zlib1.dll"):
                src = dlls_dir / name
                if src.exists():
                    shutil.copy2(src, self.python_dir / name)

            # Copy Lib/tkinter/ package
            tk_src = extract_dir / "Lib" / "tkinter"
            tk_dst = self.python_dir / "Lib" / "tkinter"
            if tk_src.exists():
                if tk_dst.exists():
                    shutil.rmtree(tk_dst)
                shutil.copytree(tk_src, tk_dst)

            # Copy tcl/ library
            tcl_src = extract_dir / "tcl"
            tcl_dst = self.python_dir / "tcl"
            if tcl_src.exists():
                if tcl_dst.exists():
                    shutil.rmtree(tcl_dst)
                shutil.copytree(tcl_src, tcl_dst)

            # Clean up
            msi_path.unlink(missing_ok=True)
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)

            # Verify
            result = subprocess.run(
                [str(self.python_exe), "-c", "import tkinter; print('ok')"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                if progress_callback:
                    progress_callback(95, 100, "tkinter ready")
                return True
            else:
                if progress_callback:
                    progress_callback(0, 100, f"tkinter verify failed: {result.stderr}")
                return False

        except Exception as e:
            msi_path.unlink(missing_ok=True)
            if extract_dir.exists():
                import shutil
                shutil.rmtree(extract_dir, ignore_errors=True)
            if progress_callback:
                progress_callback(0, 100, f"tkinter setup failed: {e}")
            return False

    def install_requirements(
        self,
        requirements_file: Path,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Install packages from a requirements.txt file."""
        if not self.is_installed:
            return False

        try:
            if progress_callback:
                progress_callback(0, 100, f"Installing from {requirements_file.name}...")

            result = subprocess.run(
                [str(self.python_exe), "-m", "pip", "install",
                 "-r", str(requirements_file)],
                capture_output=True, text=True
            )

            if result.returncode != 0:
                if progress_callback:
                    progress_callback(0, 100, f"Error: {result.stderr}")
                return False

            if progress_callback:
                progress_callback(100, 100, "Requirements installed")
            return True

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error: {e}")
            return False

    def get_python_version_string(self) -> Optional[str]:
        """Get the version string of the embedded Python."""
        if not self.python_exe.exists():
            return None
        try:
            result = subprocess.run(
                [str(self.python_exe), "--version"],
                capture_output=True, text=True
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None
