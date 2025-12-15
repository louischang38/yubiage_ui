import sys
import os
import subprocess
import threading
import time
import ctypes
import configparser
import tarfile 

# ⚠️ Cross-platform theme detection library (install: pip install darkdetect)
import darkdetect 
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QMessageBox, QFrame,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QSettings, QPoint
)
from PySide6.QtGui import QDropEvent, QColor, QFont, QIcon

# ==========================================
# ⚙️ Windows API (Import and use only on Windows)
# ==========================================
if os.name == 'nt':
    def bring_pid_to_front(pid):
        """Finds the window corresponding to the PID and forces it to the foreground (Windows only)."""
        try:
            user32 = ctypes.windll.user32
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            target_hwnd = []
            
            def enum_windows_callback(hwnd, _):
                window_pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
                if window_pid.value == pid and user32.IsWindowVisible(hwnd):
                    target_hwnd.append(hwnd)
                    return False
                return True
            
            user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
            if target_hwnd:
                hwnd = target_hwnd[0]
                user32.ShowWindow(hwnd, 9)
                user32.SetForegroundWindow(hwnd)
        except Exception as e:
            print(f"Fail to bring window to top: {e}")
else:
    def bring_pid_to_front(pid):
        # Non-Windows platform: no operation
        pass


# ==========================================
# 🎨 Colors & Styling
# ==========================================
LIGHT_THEME_COLORS = {
    "TEXT_PRIMARY": "#333333", "TEXT_SECONDARY": "#888888", "BACKGROUND": "#F7F7F7",
    "CARD_BG": "#FFFFFF", "BORDER": "#E0E0E0", "DANGER": "#D92D20", "DANGER_BG": "#FFF3F2",
    "ENCRYPT_ACCENT": "#D9534F", "ENCRYPT_BG": "#FFF8F8", "DECRYPT_ACCENT": "#5CB85C",
    "DECRYPT_BG": "#F8FFF8", "ACCENT": "#1070F0", "SUCCESS_ACCENT": "#12B76A",
    "SUCCESS_BG": "#F6FEF9",
}

DARK_THEME_COLORS = {
    "TEXT_PRIMARY": "#F0F0F0", "TEXT_SECONDARY": "#AAAAAA", "BACKGROUND": "#1E1E1E",
    "CARD_BG": "#252525", "BORDER": "#444444", "DANGER": "#FF7575", "DANGER_BG": "#3C1F1F",
    "ENCRYPT_ACCENT": "#D9534F", "ENCRYPT_BG": "#2E2323", "DECRYPT_ACCENT": "#77CC77",
    "DECRYPT_BG": "#232E23", "ACCENT": "#55AAFF", "SUCCESS_ACCENT": "#12B76A",
    "SUCCESS_BG": "#232E23",
}

def get_base_stylesheet(colors):
    clear_btn_hover_bg = colors["DANGER_BG"] if colors == LIGHT_THEME_COLORS else "#444444"
    clear_btn_hover_color = colors["DANGER"]
    progress_text_color = "transparent" if colors == LIGHT_THEME_COLORS else colors["TEXT_PRIMARY"]

    return f"""
        QMainWindow {{ background-color: {colors["BACKGROUND"]}; }}
        QLabel {{ color: {colors["TEXT_PRIMARY"]}; }}
        QPushButton {{
            border-radius: 6px; font-weight: 500; font-size: 13px; padding: 6px 12px;
            background-color: {colors["CARD_BG"]}; border: 1px solid {colors["BORDER"]};
            color: {colors["TEXT_PRIMARY"]};
        }}
        QPushButton:hover {{
            background-color: {colors["BORDER"]};
            border: 1px solid {colors["BORDER"]};
        }}
        
        /* Clear Keys Button */
        QPushButton#ClearKeysBtn {{
            color: {colors["TEXT_PRIMARY"]};
            background-color: {colors["CARD_BG"]};
            border: 1px solid {colors["BORDER"]};
        }}
        QPushButton#ClearKeysBtn:hover {{
            background-color: {colors["BORDER"]};
            border: 1px solid {colors["BORDER"]};
        }}
        
        /* Clear File/State Button */
        QPushButton#ClearBtn {{
            color: {colors["TEXT_SECONDARY"]};
            background-color: {colors["CARD_BG"]};
            border: 1px solid {colors["BORDER"]};
        }}
        QPushButton#ClearBtn:hover {{
            background-color: {clear_btn_hover_bg};
            color: {clear_btn_hover_color};
            border: 1px solid {clear_btn_hover_color};
        }}
        QProgressBar {{
            border: 1px solid {colors["BORDER"]};
            background-color: {colors["CARD_BG"]};
            border-radius: 5px;
            height: 10px;
            text-align: center;
            color: {progress_text_color};
        }}
        QProgressBar::chunk {{
            background-color: {colors["ACCENT"]};
            border-radius: 5px;
            margin: 0px;
        }}
    """

# ==========================================
# ⚡️ AgeWorker
# ==========================================
class AgeWorker(QThread):
    finished = Signal(int, int, bool)
    error = Signal(str, str) # file_name, error_message
    progress_update = Signal(float)

    def __init__(self, mode, files_to_process, recipients_keys, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.files_to_process = files_to_process
        self.recipients_keys = recipients_keys 
        self._process = None
        self.temp_files_to_cleanup = [] # Records temporary files that need cleanup

    def _create_tar_archive(self, dir_path):
        """
        Creates a temporary gzipped tar archive (.tar.gz) for a directory.
        Returns the path to the temporary .tar.gz file.
        """
        dir_name = os.path.basename(dir_path)
        tar_path = os.path.join(os.path.dirname(dir_path) or os.getcwd(), f"{dir_name}_temp_{os.getpid()}.tar.gz")
        
        try:
            with tarfile.open(tar_path, 'w:gz') as tar:
                # Adds the directory content, using the directory name as the archive root
                tar.add(dir_path, arcname=dir_name) 
            
            self.temp_files_to_cleanup.append(tar_path) 
            return tar_path
        except Exception as e:
            raise IOError(f"Failed to create TAR archive for {dir_name}: {e}")

    def run(self):
        success_count = 0
        original_files_to_process = self.files_to_process[:]
        
        # Maps the actual input file path for age to its original path
        # Format: {input_path_for_age: original_path}
        file_map = {} 
        processed_files = [] 
        total_files = 0 
        needs_clear = self.mode == "encrypt"

        try:
            # === Pre-processing: Directory Archiving (Only for Encryption) ===
            if self.mode == "encrypt":
                for original_path in original_files_to_process:
                    if os.path.isdir(original_path):
                        # Archive directory into .tar.gz
                        self.progress_update.emit(0.01)
                        tar_file_path = self._create_tar_archive(original_path) 
                        
                        processed_files.append(tar_file_path)
                        file_map[tar_file_path] = original_path # Map: Temp file -> Original directory
                    else:
                        processed_files.append(original_path)
                        file_map[original_path] = original_path # Map: Original file -> Original file
            else:
                processed_files = original_files_to_process
                for p in processed_files:
                    file_map[p] = p 

            total_files = len(processed_files)

            # === Age Encryption/Decryption Operation ===
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NEW_CONSOLE

            for i, input_path in enumerate(processed_files):
                current_file_name = os.path.basename(input_path)
                original_source_path = file_map[input_path] 
                temp_recipients_file = None
                temp_output_path = None
                temp_decrypt_path = None

                try:
                    cmd = ["age"]
                    
                    # --- Build command ---
                    if self.mode == "encrypt":
                        # 1. Age's output path uses the temporary file name
                        temp_output_path = f"{input_path}.age" 
                        cmd.append("-a")
                        cmd.extend(["-o", temp_output_path])

                        if not self.recipients_keys:
                            raise ValueError("No recipients.")

                        # Create temporary file for recipient keys
                        temp_recipients_file = os.path.join(os.path.dirname(input_path) or os.getcwd(), f".temp_recipients_{os.getpid()}.txt")
                        with open(temp_recipients_file, 'w') as f:
                            for key_path in self.recipients_keys:
                                if not os.path.exists(key_path): continue
                                with open(key_path, 'r', encoding='utf-8') as key_f:
                                    content = "".join([line for line in key_f if not line.strip().startswith('#')]).strip()
                                    if content: f.write(content + '\n')
                        
                        if not os.path.exists(temp_recipients_file) or not os.path.getsize(temp_recipients_file):
                            raise ValueError("Recipient key file is empty or invalid.")

                        cmd.extend(["-R", temp_recipients_file])
                        cmd.append(input_path)

                    else: # decrypt
                        cmd.append("-d")
                        # Base output path without .age (e.g., folder.age -> folder)
                        output_path_base = input_path.removesuffix(".age") if input_path.lower().endswith(".age") else f"{input_path}.decrypted"
                        
                        # Use a temporary output path for age to simplify post-process renaming
                        temp_decrypt_path = f"{output_path_base}.temp_decrypted_{os.getpid()}"
                        
                        cmd.extend(["-o", temp_decrypt_path])

                        if not self.recipients_keys:
                            raise ValueError("No identity.")

                        for key_path in self.recipients_keys:
                            cmd.extend(["-i", key_path])

                        cmd.append(input_path)
                    
                    # --- Execute age command ---
                    self._process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=creation_flags
                    )

                    time.sleep(0.5)
                    bring_pid_to_front(self._process.pid)

                    stdout_output, stderr_output = self._process.communicate()
                    return_code = self._process.returncode

                    if return_code == 0:
                        # === 2. Post-process (Rename/Cleanup) ===
                        if self.mode == "encrypt":
                            
                            if os.path.isdir(original_source_path):
                                # Directory encryption: Rename temp_archive.tar.gz.age -> folder.Dir.age
                                final_output_path = f"{original_source_path}.Dir.age" 
                                
                                # Rename operation
                                if os.path.exists(temp_output_path):
                                    os.makedirs(os.path.dirname(final_output_path) or '.', exist_ok=True)
                                    os.rename(temp_output_path, final_output_path)
                            # Single file encryption: No rename needed (already file.txt.age)
                            
                        else: # decrypt mode
                            # Decryption: If the original file was a simplified dir archive (e.g., folder.Dir.age)
                            # we rename the output (e.g., folder.temp_decrypted_12345) to folder.tar.gz
                            
                            # Heuristic: Check if the original encrypted file suggests it was a directory archive
                            if input_path.lower().endswith(".dir.age"):
                                # If it was a directory archive, add .tar.gz back to the base name
                                final_output_path = f"{output_path_base}.tar.gz"
                                
                                if os.path.exists(temp_decrypt_path):
                                    os.rename(temp_decrypt_path, final_output_path)
                            
                        success_count += 1
                        
                    else:
                        # Report the specific error message from age CLI output
                        error_msg = stderr_output.decode('utf-8', errors='ignore').strip()
                        detail_msg = error_msg if error_msg else f"Failed, exit code: {return_code}"
                        raise Exception(detail_msg)

                except Exception as e:
                    self.error.emit(current_file_name, str(e))
                finally:
                    progress = (i + 1) / total_files
                    self.progress_update.emit(progress)
                    # Clean up temporary recipients file
                    if temp_recipients_file and os.path.exists(temp_recipients_file):
                        try: os.remove(temp_recipients_file)
                        except: pass 
                    # Clean up temporary decrypted file if the age process failed before renaming
                    if self.mode == "decrypt" and temp_decrypt_path and os.path.exists(temp_decrypt_path):
                        try: os.remove(temp_decrypt_path)
                        except: pass

            # === 3. Cleanup: Remove temporary .tar.gz files ===
            for temp_file in self.temp_files_to_cleanup:
                try: 
                    os.remove(temp_file)
                except Exception as e:
                    print(f"Cleanup failed for {temp_file}: {e}")

        except Exception as e:
            self.error.emit("Pre-process", f"Pre-process Error: {e}")
            total_files = 0
        finally:
            self.finished.emit(success_count, total_files, needs_clear)


# ==========================================
# 🖼️ Widget: Drop Target
# ==========================================
class SingleDropTarget(QFrame):
    files_dropped = Signal(list)
    keys_dropped = Signal(list)

    def __init__(self, main_window, colors, strings, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.colors = colors
        self.strings = strings 
        self.setAcceptDrops(True)
        self.mode = "file" 

        self._apply_style()
        self.setMinimumSize(320, 180)

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel(self.strings["STR_DROP_FILE_INITIAL"], objectName="DropText", alignment=Qt.AlignCenter)
        self.label.setFont(QFont("Arial", 12))
        self.layout.addWidget(self.label)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow_color = QColor(0, 0, 0, 50) if self.colors == LIGHT_THEME_COLORS else QColor(0, 0, 0, 80)
        shadow.setColor(shadow_color)
        shadow.setOffset(QPoint(0, 5))
        self.setGraphicsEffect(shadow)
    
    def _apply_style(self, style_override=""):
         self.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {self.colors["BORDER"]};
                border-radius: 10px;
                background-color: {self.colors["CARD_BG"]};
                padding: 20px;
                {style_override}
            }}
            QLabel#DropText {{
                border: none; background-color: transparent; color: {self.colors["TEXT_SECONDARY"]};
                font-weight: 500;
            }}
        """)

    def set_mode(self, mode_type, action_text=""):
        self.mode = mode_type
        style = ""
        text_style = ""

        if mode_type == "file":
            self.label.setText(self.strings["STR_DROP_FILE_INITIAL"])
            style = f"border: 2px dashed {self.colors['BORDER']}; background-color: {self.colors['CARD_BG']};"
            text_style = f"color: {self.colors['TEXT_SECONDARY']}; font-weight: 500;"

        elif mode_type == "key":
            is_public_key = action_text == self.strings["STR_DROP_KEY_PUBLIC"]
            color = self.colors['ENCRYPT_ACCENT'] if is_public_key else self.colors['DECRYPT_ACCENT']
            bg_color = self.colors['ENCRYPT_BG'] if is_public_key else self.colors['DECRYPT_BG']
            self.label.setText(action_text)
            style = f"border: 2px dashed {color}; background-color: {bg_color};"
            text_style = f"color: {self.colors['TEXT_PRIMARY']}; font-weight: 600;"

        elif mode_type == "finished":
            style = f"border: 2px dashed {self.colors['SUCCESS_ACCENT']}; background-color: {self.colors['SUCCESS_BG']};"
            text_style = f"color: {self.colors['SUCCESS_ACCENT']}; font-weight: 700;"
            self.label.setText(self.strings["STR_DROP_FINISHED"] % action_text)

        elif mode_type == "error":
            style = f"border: 2px dashed {self.colors['DANGER']}; background-color: {self.colors['DANGER_BG']};"
            text_style = f"color: {self.colors['TEXT_PRIMARY']}; font-weight: 700;"
            self.label.setText(self.strings["STR_DROP_ERROR"] % action_text)

        self.setStyleSheet(f"""
            QFrame {{ {style} border-radius: 10px; padding: 20px; }}
            QLabel#DropText {{
                border: none; background-color: transparent; {text_style}
            }}
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: event.ignore()

    def dropEvent(self, event: QDropEvent):
        mime = event.mimeData()
        if mime.hasUrls():
            paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile() and os.path.exists(u.toLocalFile())]

            if not paths:
                event.ignore()
                return

            if self.mode in ["finished", "error"]:
                # If finished/error, start a new process by resetting the UI state 
                self.main_window._reset_state_ui(clear_keys=False)

            if self.mode == "file" or self.mode in ["finished", "error"]:
                self.files_dropped.emit(paths)
            elif self.mode == "key":
                self.keys_dropped.emit(paths)

            event.acceptProposedAction()
        else: event.ignore()


# ==========================================
# 💻 Main Window: AgeGUI
# ==========================================
class AgeGUI(QMainWindow):
    SETTINGS_FILE = "settings.ini"

    STRINGS = {
        "STR_TITLE": "YubiAge UI",
        "STR_MSGBOX_TITLE": "Message",
        "STR_STATUS_READY": "Ready. Pub Keys: %s.",
        "STR_STATUS_LOADED_KEYS": "Loaded %d keys.",
        "STR_STATUS_ENCRYPT_MODE": "Encrypt Mode",
        "STR_STATUS_DECRYPT_MODE": "Decrypt Mode",
        "STR_STATUS_START_PROCESS": "Executing (%s)...",
        "STR_STATUS_FINISHED_KEYS": "Finished. Keys: %d.",
        "STR_STATUS_ERROR_MIXED": "Terminated.",
        "STR_STATUS_ERROR_KEY_LOAD": "Key load failed.",
        "STR_STATUS_ERROR_FILE_KEY_MISSING": "File/Key missing.",
        "STR_BTN_CLEAR": "Clear State",
        "STR_BTN_CLEAR_KEYS": "Clear Keys", 
        "STR_CONFIRM_CLEAR_KEYS": "Are you sure you want to clear ALL saved public recipient key paths? They must be dropped again for future encryption.",
        "STR_ERROR_MIXED_FILES": "Do not mix .age file and directory/other file.",
        "STR_ERROR_INVALID_KEY_PATH": "Invalid key path.",
        "STR_ERROR_AGE_WORKER": "Age Worker Error: %s",
        "STR_ERROR_FILES_FAIL": "Failed! %d files failed.",
        "STR_MODE_ENCRYPT_DISPLAY": "Encryption",
        "STR_MODE_DECRYPT_DISPLAY": "Decryption",
        "STR_DROP_FILE_INITIAL": "Drop Files (or Folders for Encrypt) Here",
        "STR_DROP_KEY_PUBLIC": "Recipient key needed",
        "STR_DROP_KEY_PRIVATE": "Identity key needed",
        "STR_DROP_FINISHED": "Finished %s \n \n Drop Files (or Folders for Encrypt) Here",
        "STR_DROP_ERROR": "Failed: %s",
    }

    def __init__(self):
        super().__init__()

        # 1. Theme initialization
        self.is_dark_mode = darkdetect.isDark()
        self.colors = DARK_THEME_COLORS if self.is_dark_mode else LIGHT_THEME_COLORS
        self.strings = self.STRINGS

        self.setWindowTitle(self.strings["STR_TITLE"])
        
        # Fixed window size
        self.setFixedSize(450, 320)

        # State variables
        self.keys = []                  
        self.recipients_keys = []       
        self.files_to_process = []
        self.current_action_mode = None
        self._key_pending = False
        self.worker = None

        # 2. Apply initial theme
        self.setStyleSheet(get_base_stylesheet(self.colors))
        self._set_qmessagebox_style()

        self._init_ui()
        self._load_key_settings()

    def _set_qmessagebox_style(self):
        """Configures the style of QMessageBox to match the current theme."""
        text_color = self.colors["TEXT_PRIMARY"]
        bg_color = self.colors["CARD_BG"]
        btn_bg = self.colors["CARD_BG"]
        btn_text = self.colors["TEXT_PRIMARY"]
        
        style = f"""
            QMessageBox {{
                background-color: {bg_color};
            }}
            QMessageBox QLabel {{
                color: {text_color};
            }}
            QMessageBox QPushButton {{
                border-radius: 6px; font-weight: 500; padding: 6px 12px;
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {self.colors['BORDER']};
            }}
            QMessageBox QPushButton:hover {{
                background-color: {self.colors['BORDER']};
            }}
        """

        app = QApplication.instance()
        current_style = app.styleSheet()
        new_style = current_style.split("QMessageBox {")[0] + style
        app.setStyleSheet(new_style)

    def _get_settings_path(self):
        # Determine settings file path 
        if getattr(sys, 'frozen', False):
            return os.path.join(os.path.dirname(sys.executable), self.SETTINGS_FILE)
        else:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), self.SETTINGS_FILE)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        self.drop_target = SingleDropTarget(
            main_window=self, 
            colors=self.colors, 
            strings=self.STRINGS, 
            parent=central
        )
        self.drop_target.files_dropped.connect(self._on_files_dropped)
        self.drop_target.keys_dropped.connect(self._on_keys_dropped_in_key_mode)
        self.main_layout.addWidget(self.drop_target, 1)

        self.progress = QProgressBar(value=0)
        self.main_layout.addWidget(self.progress)

        footer_layout = QHBoxLayout()
        self.status_label = QLabel(self.strings["STR_STATUS_READY"] % "0", alignment=Qt.AlignVCenter)
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setStyleSheet(f"color: {self.colors['TEXT_SECONDARY']};")
        footer_layout.addWidget(self.status_label, 1)
        
        self.btn_clear_keys = QPushButton(self.strings["STR_BTN_CLEAR_KEYS"], objectName="ClearKeysBtn")
        self.btn_clear_keys.clicked.connect(self._clear_keys_action)
        self.btn_clear_keys.setFixedSize(100, 28)
        footer_layout.addWidget(self.btn_clear_keys)

        self.btn_clear = QPushButton(self.strings["STR_BTN_CLEAR"], objectName="ClearBtn")
        self.btn_clear.clicked.connect(lambda: self._reset_state_ui(clear_keys=False))
        self.btn_clear.setFixedSize(90, 28)
        footer_layout.addWidget(self.btn_clear)

        self.main_layout.addLayout(footer_layout)

    def _reset_state_ui(self, clear_keys=False):
        """Resets the UI and file/state."""
        self.files_to_process = []
        self._key_pending = False
        self.current_action_mode = None
        self.keys = [] 
        self.progress.setValue(0)
        self.drop_target.setDisabled(False)
        self.btn_clear.setDisabled(False)
        self.btn_clear_keys.setDisabled(False)

        self.drop_target.set_mode("file")

        if clear_keys:
            self.recipients_keys = [] 

        key_status = str(len(self.recipients_keys))
        self.status_label.setText(self.strings["STR_STATUS_READY"] % key_status)

    def _clear_keys_action(self):
        """
        Clears the loaded public/identity keys and updates persistent settings, 
        with a confirmation dialog.
        """
        if not self.recipients_keys:
            # If no keys are loaded, just clear the UI state if needed and return.
            self.status_label.setText(self.strings["STR_STATUS_READY"] % "0")
            return

        # Confirmation Dialog
        reply = QMessageBox.question(
            self, 
            self.strings["STR_BTN_CLEAR_KEYS"], # Dialog Title
            self.strings["STR_CONFIRM_CLEAR_KEYS"], # Dialog Text
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No # Default button is No
        )

        if reply == QMessageBox.Yes:
            self.recipients_keys = []
            self._save_key_settings([], False) 

            self.keys = []

            if self._key_pending:
                self._reset_state_ui(clear_keys=False) 

            self.status_label.setText(self.strings["STR_STATUS_READY"] % "0")
        else:
            # User clicked No, do nothing
            pass


    def _load_key_settings(self):
        settings = QSettings(self._get_settings_path(), QSettings.IniFormat)
        is_remembered = settings.value("Keys/RememberKeys", "false") == "true"

        if is_remembered:
            key_paths_str = settings.value("Keys/Paths", "")
            key_paths = [p for p in key_paths_str.split(';') if os.path.exists(p) and p]

            if key_paths:
                self.recipients_keys = key_paths 
                self.status_label.setText(self.strings["STR_STATUS_LOADED_KEYS"] % len(self.recipients_keys))

    def _save_key_settings(self, keys_to_save: list, remember: bool):
        settings = QSettings(self._get_settings_path(), QSettings.IniFormat)
        settings.setValue("Keys/RememberKeys", "true" if remember else "false")

        if remember:
            settings.setValue("Keys/Paths", ";".join(keys_to_save))
        else:
            settings.setValue("Keys/Paths", "")

        settings.sync()

    def _on_files_dropped(self, paths):
        if self._key_pending: return

        has_dirs = any(os.path.isdir(p) for p in paths)
        has_age_files = any(p.lower().endswith(".age") for p in paths)
        
        # 1. Error check: Do not mix .age files with directories or other files
        if (has_dirs and has_age_files) or (has_age_files and any(not p.lower().endswith(".age") and not os.path.isdir(p) for p in paths)):
             self.drop_target.set_mode("error", self.strings["STR_ERROR_MIXED_FILES"])
             self.status_label.setText(self.strings["STR_STATUS_ERROR_MIXED"])
             return
        
        # Determine mode
        if has_age_files:
            self.current_action_mode = "decrypt"
        else:
            self.current_action_mode = "encrypt"

        self.files_to_process = paths
        self.keys = [] 

        if self.current_action_mode == "decrypt":
            # Decrypt Mode
            self._key_pending = True
            self.drop_target.set_mode("key", self.strings["STR_DROP_KEY_PRIVATE"])
            self.status_label.setText(self.strings["STR_STATUS_DECRYPT_MODE"])
        else:
            # Encrypt Mode (including directories and files)
            if not self.recipients_keys: 
                self._key_pending = True
                self.drop_target.set_mode("key", self.strings["STR_DROP_KEY_PUBLIC"])
                self.status_label.setText(self.strings["STR_STATUS_ENCRYPT_MODE"])
            else:
                # Use remembered public keys
                self.keys = list(self.recipients_keys)
                self.status_label.setText(f"{self.strings['STR_STATUS_LOADED_KEYS'] % len(self.keys)} {self.strings['STR_STATUS_START_PROCESS'] % 'encrypt'}")
                self._start_process()

    def _on_keys_dropped_in_key_mode(self, paths):
        if not self._key_pending: return

        valid_key_paths = [p for p in paths if os.path.exists(p)]

        if not valid_key_paths:
            self.drop_target.set_mode("error", self.strings["STR_ERROR_INVALID_KEY_PATH"])
            self.status_label.setText(self.strings["STR_STATUS_ERROR_KEY_LOAD"])
            self.drop_target.setDisabled(False)
            return

        self.keys = valid_key_paths
        self._key_pending = False

        if self.current_action_mode == "encrypt":
            self.recipients_keys = valid_key_paths 
            self._save_key_settings(self.recipients_keys, True)
            self.status_label.setText(f"{self.strings['STR_STATUS_LOADED_KEYS'] % len(self.recipients_keys)} {self.strings['STR_STATUS_START_PROCESS'] % 'encrypt'}")
        elif self.current_action_mode == "decrypt":
            self.status_label.setText(f"{self.strings['STR_STATUS_LOADED_KEYS'] % len(self.keys)} {self.strings['STR_STATUS_START_PROCESS'] % 'decrypt'}")

        self._start_process()

    def _start_process(self):
        if not self.files_to_process or not self.keys:
            self.drop_target.set_mode("error", self.strings["STR_STATUS_ERROR_FILE_KEY_MISSING"])
            self._reset_state_ui(clear_keys=False) 
            return

        self.drop_target.setDisabled(True)
        self.btn_clear.setDisabled(True)
        self.btn_clear_keys.setDisabled(True)

        mode_text = 'encrypt' if self.current_action_mode == 'encrypt' else 'decrypt'
        self.status_label.setText(self.strings["STR_STATUS_START_PROCESS"] % mode_text)
        self.progress.setRange(0, 0) # Indeterminate progress bar

        self.worker = AgeWorker(self.current_action_mode, self.files_to_process, self.keys)
        self.worker.finished.connect(self._on_finished)

        def report_error(file_name, error_msg):
            formatted_error = self.strings["STR_ERROR_AGE_WORKER"] % error_msg
            QMessageBox.critical(self, self.strings["STR_MSGBOX_TITLE"], f"File: {file_name}\n\n{formatted_error}")
            
        self.worker.error.connect(report_error)
        self.worker.progress_update.connect(self._update_progress)
        self.worker.start()

    def _update_progress(self, val):
        self.progress.setRange(0, 100)
        self.progress.setValue(int(val * 100))

    def _on_finished(self, success, total, needs_clear):
        self.progress.setValue(100)
        self.drop_target.setDisabled(False)
        self.btn_clear.setDisabled(False)
        self.btn_clear_keys.setDisabled(False)

        if total == 0:
            # Pre-process error (e.g., tar failed)
            self.drop_target.set_mode("error", self.strings["STR_STATUS_ERROR_MIXED"])
            self.status_label.setText(self.strings["STR_STATUS_ERROR_MIXED"])
            self._reset_state_ui(clear_keys=False) # Error: Reset immediately
            
        elif success == total:
            # Success
            if self.current_action_mode == 'encrypt':
                mode_text_display = self.strings["STR_MODE_ENCRYPT_DISPLAY"]
                key_count = len(self.recipients_keys) 
            else:
                mode_text_display = self.strings["STR_MODE_DECRYPT_DISPLAY"]
                key_count = 0 

            # Show success message and status, DO NOT reset state immediately
            self.drop_target.set_mode("finished", mode_text_display)
            self.status_label.setText(self.strings["STR_STATUS_FINISHED_KEYS"] % key_count)
            
            # If decrypting, keys are temporary for the operation, we can clear them.
            if self.current_action_mode == "decrypt":
                self.files_to_process = []
                self.keys = []
            
        else:
            # Partial or total failure of age process
            error_count = total - success
            self.drop_target.set_mode("error", self.strings["STR_ERROR_FILES_FAIL"] % error_count)
            self.status_label.setText(self.strings["STR_STATUS_ERROR_MIXED"])
            self._reset_state_ui(clear_keys=False) # Failure: Reset immediately


if __name__ == "__main__":
    if os.name == 'nt':
        # Disable the default age prompt on Windows for better UI integration
        os.environ["AGE_DISABLE_PTE"] = "1" 

    try:
        app = QApplication(sys.argv)
    except RuntimeError:
        app = QApplication.instance()

    font = QFont("Arial", 10)
    if sys.platform == "darwin": font = QFont("Helvetica", 10)
    app.setFont(font)

    window = AgeGUI()

    icon_path = "icon.ico"
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        icon_path = os.path.join(base_path, "icon.ico")

    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))

    window.show()
    sys.exit(app.exec())
