"""
Deployment Package Generator

Takes user configuration and generates a complete portable deployment package.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, List

from core.python_manager import PYTHON_VERSIONS, get_python_url, get_pth_zip_name
from core.template_engine import render_template

# Where templates live relative to this file
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

GIT_VERSION = "2.47.1"
GIT_URL = f"https://github.com/git-for-windows/git/releases/download/v{GIT_VERSION}.windows.1/MinGit-{GIT_VERSION}-64-bit.zip"

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


@dataclass
class PackageConfig:
    """Configuration for a deployment package."""
    project_name: str = "MyProject"
    python_minor: str = "3.12"                # e.g., "3.12"
    output_dir: Path = Path(".")
    entry_point: str = "app.py"
    launcher_name: str = "launcher.bat"
    requirements: str = ""                     # requirements.txt content
    include_git: bool = False
    include_ffmpeg: bool = False
    include_tkinter: bool = True
    extra_pth_paths: List[str] = field(default_factory=list)
    extra_pip_args: str = ""                   # e.g., "--index-url https://..."

    @property
    def python_version(self) -> str:
        return PYTHON_VERSIONS.get(self.python_minor, "3.12.8")

    @property
    def python_url(self) -> str:
        return get_python_url(self.python_version)

    @property
    def pth_zip_name(self) -> str:
        return get_pth_zip_name(self.python_minor)


class PackageGenerator:
    """Generates a complete portable deployment package."""

    def __init__(self, config: PackageConfig):
        self.config = config
        self.output_path = config.output_dir / config.project_name.replace(" ", "_")

    def generate(self, progress_callback: Optional[Callable] = None) -> bool:
        """Generate the full deployment package.

        Args:
            progress_callback: Optional callback(current, total, message)

        Returns:
            True if generation succeeded.
        """
        try:
            if progress_callback:
                progress_callback(0, 100, "Creating package directory...")

            self.output_path.mkdir(parents=True, exist_ok=True)

            # Generate install.bat
            if progress_callback:
                progress_callback(10, 100, "Generating install.bat...")
            self._generate_install_bat()

            # Generate launcher.bat
            if progress_callback:
                progress_callback(30, 100, "Generating launcher.bat...")
            self._generate_launcher_bat()

            # Generate config.py
            if progress_callback:
                progress_callback(50, 100, "Generating config.py...")
            self._generate_config_py()

            # Write requirements.txt
            if progress_callback:
                progress_callback(70, 100, "Writing requirements.txt...")
            self._write_requirements()

            # Write stub entry point if it doesn't exist
            if progress_callback:
                progress_callback(85, 100, "Creating entry point stub...")
            self._write_entry_point_stub()

            if progress_callback:
                progress_callback(100, 100, f"Package generated at: {self.output_path}")
            return True

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, f"Error: {e}")
            return False

    def _generate_install_bat(self):
        """Generate the parameterized install.bat."""
        template = (TEMPLATES_DIR / "install.bat.template").read_text(encoding="utf-8")

        # Build conditional sections
        tkinter_echo = 'echo   - Tkinter GUI framework\n' if self.config.include_tkinter else ''
        git_echo = 'echo   - Portable Git\n' if self.config.include_git else ''
        ffmpeg_echo = 'echo   - Portable FFmpeg\n' if self.config.include_ffmpeg else ''

        # Git variables
        git_vars = ''
        if self.config.include_git:
            git_vars = (
                f'set "GIT_DIR=%SCRIPT_DIR%git_portable"\n'
                f'set "GIT_EXE=%GIT_DIR%\\cmd\\git.exe"\n'
                f'set "GIT_VERSION={GIT_VERSION}"\n'
                f'set "GIT_URL={GIT_URL}"\n'
                f'set "GIT_ZIP=%SCRIPT_DIR%git_portable.zip"\n\n'
            )

        # FFmpeg variables
        ffmpeg_vars = ''
        if self.config.include_ffmpeg:
            ffmpeg_vars = (
                'set "FFMPEG_DIR=%SCRIPT_DIR%ffmpeg_portable"\n'
                'set "FFMPEG_EXE=%FFMPEG_DIR%\\bin\\ffmpeg.exe"\n'
                f'set "FFMPEG_URL={FFMPEG_URL}"\n'
                'set "FFMPEG_ZIP=%SCRIPT_DIR%ffmpeg_portable.zip"\n\n'
            )

        # PTH extra paths
        pth_extra = ''
        if self.config.extra_pth_paths:
            for p in self.config.extra_pth_paths:
                pth_extra += f", '{p}'"

        # Tkinter section
        tkinter_section = ''
        if self.config.include_tkinter:
            tkinter_section = self._get_tkinter_section()

        # Git section
        git_section = ''
        if self.config.include_git:
            git_section = self._get_git_section()

        # FFmpeg section
        ffmpeg_section = ''
        if self.config.include_ffmpeg:
            ffmpeg_section = self._get_ffmpeg_section()

        # PATH setup
        path_setup = ''
        if self.config.include_git:
            path_setup += (
                'if exist "%GIT_EXE%" (\n'
                '    set "PATH=%GIT_DIR%\\cmd;%PATH%"\n'
                '    echo [OK] Portable Git added to PATH.\n'
                ')\n\n'
            )
        if self.config.include_ffmpeg:
            path_setup += (
                'if exist "%FFMPEG_EXE%" (\n'
                '    set "PATH=%FFMPEG_DIR%\\bin;%PATH%"\n'
                '    echo [OK] Portable FFmpeg added to PATH.\n'
                ')\n\n'
            )

        variables = {
            "PROJECT_NAME": self.config.project_name,
            "PYTHON_VERSION": self.config.python_version,
            "PYTHON_URL": self.config.python_url,
            "ENTRY_POINT": self.config.entry_point,
            "PTH_ZIP_NAME": self.config.pth_zip_name,
            "PTH_EXTRA": pth_extra,
            "TKINTER_ECHO": tkinter_echo,
            "GIT_ECHO": git_echo,
            "FFMPEG_ECHO": ffmpeg_echo,
            "GIT_VARS": git_vars,
            "FFMPEG_VARS": ffmpeg_vars,
            "TKINTER_SECTION": tkinter_section,
            "GIT_SECTION": git_section,
            "FFMPEG_SECTION": ffmpeg_section,
            "PATH_SETUP": path_setup,
        }

        rendered = render_template(template, variables)
        (self.output_path / "install.bat").write_text(rendered, encoding="utf-8")

    def _generate_launcher_bat(self):
        """Generate the parameterized launcher.bat."""
        template = (TEMPLATES_DIR / "launcher.bat.template").read_text(encoding="utf-8")

        path_setup = ''
        if self.config.include_git:
            path_setup += (
                'if exist "%SCRIPT_DIR%git_portable\\cmd\\git.exe" (\n'
                '    set "PATH=%SCRIPT_DIR%git_portable\\cmd;%PATH%"\n'
                ')\n'
            )
        if self.config.include_ffmpeg:
            path_setup += (
                'if exist "%SCRIPT_DIR%ffmpeg_portable\\bin\\ffmpeg.exe" (\n'
                '    set "PATH=%SCRIPT_DIR%ffmpeg_portable\\bin;%PATH%"\n'
                ')\n'
            )

        variables = {
            "PROJECT_NAME": self.config.project_name,
            "ENTRY_POINT": self.config.entry_point,
            "LAUNCHER_NAME": self.config.launcher_name,
            "PATH_SETUP": path_setup,
        }

        rendered = render_template(template, variables)
        out_name = self.config.launcher_name
        (self.output_path / out_name).write_text(rendered, encoding="utf-8")

    def _generate_config_py(self):
        """Generate the parameterized config.py."""
        template = (TEMPLATES_DIR / "config.py.template").read_text(encoding="utf-8")

        extra_path_vars = ''
        extra_resolve_funcs = ''
        extra_resolved_vars = ''

        if self.config.include_git:
            extra_path_vars += 'GIT_PORTABLE_DIR = BASE_DIR / "git_portable"\n'
            extra_resolve_funcs += (
                '\ndef _resolve_git_path() -> str:\n'
                '    """Find the best available git executable."""\n'
                '    portable_git = GIT_PORTABLE_DIR / "cmd" / "git.exe"\n'
                '    if portable_git.exists():\n'
                '        return str(portable_git)\n'
                '    return "git"\n\n'
            )
            extra_resolved_vars += 'GIT_PATH = _resolve_git_path()\n'

        if self.config.include_ffmpeg:
            extra_path_vars += 'FFMPEG_PORTABLE_DIR = BASE_DIR / "ffmpeg_portable"\n'
            extra_resolve_funcs += (
                '\ndef _resolve_ffmpeg_path() -> str:\n'
                '    """Find the best available ffmpeg executable."""\n'
                '    portable_ffmpeg = FFMPEG_PORTABLE_DIR / "bin" / "ffmpeg.exe"\n'
                '    if portable_ffmpeg.exists():\n'
                '        return str(portable_ffmpeg)\n'
                '    return "ffmpeg"\n\n'
            )
            extra_resolved_vars += 'FFMPEG_PATH = _resolve_ffmpeg_path()\n'

        variables = {
            "PROJECT_NAME": self.config.project_name,
            "EXTRA_PATH_VARS": extra_path_vars,
            "EXTRA_RESOLVE_FUNCS": extra_resolve_funcs,
            "EXTRA_RESOLVED_VARS": extra_resolved_vars,
        }

        rendered = render_template(template, variables)
        (self.output_path / "config.py").write_text(rendered, encoding="utf-8")

    def _write_requirements(self):
        """Write requirements.txt."""
        content = self.config.requirements.strip()
        if not content:
            content = "# Add your dependencies here\n# example: requests>=2.31.0\n"
        (self.output_path / "requirements.txt").write_text(content + "\n", encoding="utf-8")

    def _write_entry_point_stub(self):
        """Write a stub entry point file if it doesn't exist."""
        entry = self.output_path / self.config.entry_point
        if entry.exists():
            return

        if self.config.include_tkinter:
            content = (
                f'"""\n{self.config.project_name} - Main Application\n'
                f'Generated by Auto Portable Python Deployer\n"""\n\n'
                'import tkinter as tk\n'
                'from tkinter import ttk\n\n\n'
                'def main():\n'
                f'    root = tk.Tk()\n'
                f'    root.title("{self.config.project_name}")\n'
                f'    root.geometry("800x600")\n\n'
                f'    label = ttk.Label(root, text="Welcome to {self.config.project_name}!",\n'
                f'                      font=("Segoe UI", 16))\n'
                f'    label.pack(expand=True)\n\n'
                f'    root.mainloop()\n\n\n'
                'if __name__ == "__main__":\n'
                '    main()\n'
            )
        else:
            content = (
                f'"""\n{self.config.project_name} - Main Application\n'
                f'Generated by Auto Portable Python Deployer\n"""\n\n\n'
                'def main():\n'
                f'    print("Welcome to {self.config.project_name}!")\n\n\n'
                'if __name__ == "__main__":\n'
                '    main()\n'
            )
        entry.write_text(content, encoding="utf-8")

    def _get_tkinter_section(self) -> str:
        """Generate the tkinter setup section for install.bat."""
        return (
            ':: ============================================\n'
            ':: Set up tkinter (needed for GUI)\n'
            ':: ============================================\n'
            '"%PYTHON_EXE%" -c "import _tkinter" >nul 2>&1\n'
            'if %errorlevel% neq 0 (\n'
            '    echo [STEP] Setting up tkinter for GUI...\n'
            '\n'
            '    set "TCLTK_MSI_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/amd64/tcltk.msi"\n'
            '    set "TCLTK_MSI=%SCRIPT_DIR%_tcltk.msi"\n'
            '    set "TCLTK_DIR=%SCRIPT_DIR%_tcltk_extract"\n'
            '\n'
            '    echo   Downloading tcltk.msi...\n'
            '    powershell -NoProfile -ExecutionPolicy Bypass -Command ^\n'
            '        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^\n'
            "        \"$ProgressPreference = 'SilentlyContinue';\" ^\n"
            "        \"Invoke-WebRequest -Uri '!TCLTK_MSI_URL!' -OutFile '!TCLTK_MSI!'\"\n"
            '\n'
            '    if not exist "!TCLTK_MSI!" (\n'
            '        echo WARNING: Failed to download tcltk.msi. GUI may not work.\n'
            '        goto :tkinter_done\n'
            '    )\n'
            '\n'
            '    echo   Extracting tkinter components...\n'
            '    if exist "!TCLTK_DIR!" rmdir /S /Q "!TCLTK_DIR!" 2>nul\n'
            "    powershell -NoProfile -Command \"Start-Process -FilePath 'msiexec.exe' -ArgumentList '/a','!TCLTK_MSI!','/qn','TARGETDIR=!TCLTK_DIR!' -Wait -NoNewWindow\"\n"
            '\n'
            '    :: Copy DLLs next to python.exe\n'
            '    if exist "!TCLTK_DIR!\\DLLs\\_tkinter.pyd" (\n'
            '        copy /Y "!TCLTK_DIR!\\DLLs\\_tkinter.pyd" "%PYTHON_DIR%\\" >nul 2>&1\n'
            '        copy /Y "!TCLTK_DIR!\\DLLs\\tcl86t.dll" "%PYTHON_DIR%\\" >nul 2>&1\n'
            '        copy /Y "!TCLTK_DIR!\\DLLs\\tk86t.dll" "%PYTHON_DIR%\\" >nul 2>&1\n'
            '        if exist "!TCLTK_DIR!\\DLLs\\zlib1.dll" (\n'
            '            copy /Y "!TCLTK_DIR!\\DLLs\\zlib1.dll" "%PYTHON_DIR%\\" >nul 2>&1\n'
            '        )\n'
            '    )\n'
            '\n'
            '    :: Copy Lib/tkinter/ Python package\n'
            '    if exist "!TCLTK_DIR!\\Lib\\tkinter" (\n'
            '        if exist "%PYTHON_DIR%\\Lib\\tkinter" rmdir /S /Q "%PYTHON_DIR%\\Lib\\tkinter" 2>nul\n'
            '        xcopy /E /I /Y "!TCLTK_DIR!\\Lib\\tkinter" "%PYTHON_DIR%\\Lib\\tkinter" >nul 2>&1\n'
            '    )\n'
            '\n'
            '    :: Copy tcl/ library\n'
            '    if exist "!TCLTK_DIR!\\tcl" (\n'
            '        if exist "%PYTHON_DIR%\\tcl" rmdir /S /Q "%PYTHON_DIR%\\tcl" 2>nul\n'
            '        xcopy /E /I /Y "!TCLTK_DIR!\\tcl" "%PYTHON_DIR%\\tcl" >nul 2>&1\n'
            '    )\n'
            '\n'
            '    :: Cleanup\n'
            '    rmdir /S /Q "!TCLTK_DIR!" 2>nul\n'
            '    del "!TCLTK_MSI!" 2>nul\n'
            '\n'
            '    :: Verify\n'
            '    "%PYTHON_EXE%" -c "import _tkinter" >nul 2>&1\n'
            '    if errorlevel 1 (\n'
            '        echo WARNING: Failed to set up tkinter. GUI may not work.\n'
            '    ) else (\n'
            '        echo [OK] tkinter setup complete.\n'
            '    )\n'
            ') else (\n'
            '    echo [OK] tkinter already available.\n'
            ')\n'
            ':tkinter_done\n\n'
        )

    def _get_git_section(self) -> str:
        """Generate the Git download section for install.bat."""
        return (
            ':: ============================================\n'
            ':: Download Portable Git\n'
            ':: ============================================\n'
            'if exist "%GIT_EXE%" (\n'
            '    echo [OK] Portable Git already installed.\n'
            '    goto :git_done\n'
            ')\n'
            '\n'
            'echo [STEP] Downloading portable Git %GIT_VERSION%...\n'
            'powershell -NoProfile -ExecutionPolicy Bypass -Command ^\n'
            '    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^\n'
            "    \"$ProgressPreference = 'SilentlyContinue';\" ^\n"
            "    \"Invoke-WebRequest -Uri '%GIT_URL%' -OutFile '%GIT_ZIP%'\"\n"
            '\n'
            'if not exist "%GIT_ZIP%" (\n'
            '    echo WARNING: Failed to download Git. Git features may not work.\n'
            '    goto :git_done\n'
            ')\n'
            '\n'
            'echo [STEP] Extracting portable Git...\n'
            'powershell -NoProfile -ExecutionPolicy Bypass -Command ^\n'
            "    \"Expand-Archive -Path '%GIT_ZIP%' -DestinationPath '%GIT_DIR%' -Force\"\n"
            '\n'
            'del "%GIT_ZIP%" 2>nul\n'
            ':git_done\n\n'
        )

    def _get_ffmpeg_section(self) -> str:
        """Generate the FFmpeg download section for install.bat."""
        return (
            ':: ============================================\n'
            ':: Download Portable FFmpeg\n'
            ':: ============================================\n'
            'if exist "%FFMPEG_EXE%" (\n'
            '    echo [OK] Portable FFmpeg already installed.\n'
            '    goto :ffmpeg_done\n'
            ')\n'
            '\n'
            'echo [STEP] Downloading portable FFmpeg...\n'
            'powershell -NoProfile -ExecutionPolicy Bypass -Command ^\n'
            '    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^\n'
            "    \"$ProgressPreference = 'SilentlyContinue';\" ^\n"
            "    \"Invoke-WebRequest -Uri '%FFMPEG_URL%' -OutFile '%FFMPEG_ZIP%'\"\n"
            '\n'
            'if not exist "%FFMPEG_ZIP%" (\n'
            '    echo WARNING: Failed to download FFmpeg.\n'
            '    goto :ffmpeg_done\n'
            ')\n'
            '\n'
            'echo [STEP] Extracting portable FFmpeg...\n'
            'powershell -NoProfile -ExecutionPolicy Bypass -Command ^\n'
            "    \"$tempDir = '%SCRIPT_DIR%_ffmpeg_temp';\" ^\n"
            "    \"Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath $tempDir -Force;\" ^\n"
            '    "$inner = Get-ChildItem $tempDir -Directory | Select-Object -First 1;" ^\n'
            "    \"if ($inner -and (Test-Path (Join-Path $inner.FullName 'bin'))) {\" ^\n"
            "    \"  New-Item -Path '%FFMPEG_DIR%\\bin' -ItemType Directory -Force | Out-Null;\" ^\n"
            "    \"  Copy-Item (Join-Path $inner.FullName 'bin\\*') '%FFMPEG_DIR%\\bin\\' -Force;\" ^\n"
            "    \"  Write-Host '   Extracted FFmpeg to ffmpeg_portable\\bin\\'\" ^\n"
            '    "} else {" ^\n'
            "    \"  Write-Host 'WARNING: FFmpeg zip has unexpected structure'\" ^\n"
            '    "};\" ^\n'
            "    \"Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue\"\n"
            '\n'
            'del "%FFMPEG_ZIP%" 2>nul\n'
            ':ffmpeg_done\n\n'
        )
