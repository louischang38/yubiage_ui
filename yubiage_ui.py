import sys
import os
import subprocess
import threading
import time
import ctypes
import configparser
import re 

# Cross-platform theme detection library (install: pip install darkdetect)
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
# Windows API (Import and use only on Windows)
# ==========================================
if os.name == 'nt':
    def bring_pid_to_front(pid):
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
        pass


# ==========================================
# 🎨 Colors & Styling
# ==========================================
LIGHT_THEME_COLORS = {
    "TEXT_PRIMARY": "#333333", "TEXT_SECONDARY": "#888888", "BACKGROUND": "#F7F7F7",
    "CARD_BG": "#FFFFFF", "BORDER": "#E0E0E0", "DANGER": "#D92D20", "DANGER_BG": "#FFF3F2",
    "ENCRYPT_ACCENT": "#D9534F", "ENCRYPT_BG": "#FFF8FF", "DECRYPT_ACCENT": "#5CB85C",
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
            color: {colors["TEXT_SECONDARY"]}; 
            background-color: {colors["CARD_BG"]};
            border: 1px solid {colors["BORDER"]};
        }}
        QPushButton#ClearKeysBtn:hover {{
            background-color: {colors["BORDER"]};
            border: 1px solid {colors["BORDER"]};
        }}
        
        /* Clear File/State Button */
        QPushButton#ClearBtn {{
            color: {colors["TEXT_PRIMARY"]}; 
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
#  AgeWorker
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

    def _find_unique_filename(self, path):
        """
        Find a unique filename by appending (n) to the extension to avoid conflicts.
        """
        if not os.path.exists(path):
            return path

        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        
        name, ext = os.path.splitext(filename)
        match = re.search(r' \((\d+)\)$', name)
        
        if match:
            base_name_without_suffix = name[:match.start()]
            start_num = int(match.group(1)) + 1
        else:
            base_name_without_suffix = name
            start_num = 1
        
        while True:
            new_name = f"{base_name_without_suffix} ({start_num}){ext}"
            new_path = os.path.join(directory, new_name)
            
            if not os.path.exists(new_path):
                return new_path
            
            start_num += 1

    def run(self):
        success_count = 0
        processed_files = self.files_to_process[:]
        total_files = len(processed_files) 
        needs_clear = self.mode == "encrypt"

        try:
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NEW_CONSOLE

            for i, input_path in enumerate(processed_files):
                current_file_name = os.path.basename(input_path)
                temp_recipients_file = None
                temp_output_path = None
                temp_decrypt_path = None
                output_path_base = ""

                try:
                    cmd = ["age"]
                    
                    # --- Build command ---
                    if self.mode == "encrypt":
                        temp_output_path = f"{input_path}.age" 
                            
                        cmd.append("-a")
                        cmd.extend(["-o", temp_output_path])

                        if not self.recipients_keys:
                            raise ValueError("No recipients.")

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
                        output_path_base = input_path.removesuffix(".age") if input_path.lower().endswith(".age") else f"{input_path}.decrypted"
                        
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
                            pass
                            
                        else: # decrypt mode
                            
                            # === File conflict detected (automatically append numeric suffix) ===
                            if input_path.lower().endswith(".age"):
                                
                                if os.path.exists(temp_decrypt_path):
                                    
                                    expected_output_path = output_path_base 
                                    final_output_path = self._find_unique_filename(expected_output_path)
                                        
                                    os.rename(temp_decrypt_path, final_output_path)

                                else:
                                    raise IOError(f"Age returned success, but output file not found: {temp_decrypt_path}")
                            
                        success_count += 1
                        
                    else:
                        error_msg = stderr_output.decode('utf-8', errors='ignore').strip()
                        detail_msg = error_msg if error_msg else f"Failed, exit code: {return_code}"
                        raise Exception(detail_msg)

                except Exception as e:
                    self.error.emit(current_file_name, str(e))
                finally:
                    progress = (i + 1) / total_files
                    self.progress_update.emit(progress)
                    
                    if temp_recipients_file and os.path.exists(temp_recipients_file):
                        try: os.remove(temp_recipients_file)
                        except: pass 
                        
                    if self.mode == "decrypt" and temp_decrypt_path and os.path.exists(temp_decrypt_path):
                        try: 
                            os.remove(temp_decrypt_path)
                        except: 
                            pass


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
     
        self.label = QLabel(self.strings["STR_DROP_FILE_ENCRYPT"], objectName="DropText", alignment=Qt.AlignCenter)
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
            }}
            QLabel#DropText {{
                border: none; background-color: transparent; color: {self.colors["TEXT_SECONDARY"]};
                font-weight: 500;
            }}
            {style_override}
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): 
            event.acceptProposedAction()
        else: 
            event.ignore()

    def set_mode(self, mode, message=None):
        """Sets the drop target mode and updates the message."""
        self.mode = mode
        
        style_override = ""
        new_text = ""
        text_color = self.colors["TEXT_SECONDARY"]

        if mode == "file":
          
            if self.main_window.current_action_mode == "decrypt":
                new_text = self.strings["STR_DROP_FILE_DECRYPT"]
            else:
                new_text = self.strings["STR_DROP_FILE_ENCRYPT"]
        elif mode == "key":
            new_text = message if message else self.strings["STR_DROP_KEY_PUBLIC"] 
        elif mode == "finished":
            accent = self.colors["SUCCESS_ACCENT"]
            bg = self.colors["SUCCESS_BG"]
            new_text = self.strings["STR_DROP_FINISHED"] % message
            style_override = f"border: 2px solid {accent}; background-color: {bg};"
            text_color = accent
        elif mode == "error":
            accent = self.colors["DANGER"]
            bg = self.colors["DANGER_BG"]
            new_text = self.strings["STR_DROP_ERROR"] % message
            style_override = f"border: 2px solid {accent}; background-color: {bg};"
            text_color = accent
        
        self._apply_style(style_override)
        self.label.setText(new_text)
        self.label.setStyleSheet(f"color: {text_color}; font-weight: 500;")


    def dropEvent(self, event: QDropEvent):
        mime = event.mimeData()
        if mime.hasUrls():
        
            paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile() and os.path.exists(u.toLocalFile())]

            if not paths:
                event.ignore()
                return

            if self.mode in ["finished", "error"]:
                self.main_window._reset_state_ui(clear_keys=False)

            if self.mode == "file":
             
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
        "STR_TITLE": "YubiAge UI v0.1.1",
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
        "STR_ERROR_MIXED_FILES": "Do not mix .age file and non-.age file.",
        "STR_ERROR_INVALID_KEY_PATH": "Invalid key path.",
        "STR_ERROR_AGE_WORKER": "Age Worker Error: %s",
        "STR_ERROR_FILES_FAIL": "Failed! %d files failed.",
        "STR_ERROR_DECRYPT_MULTI": "One file at a time (no folders)", 
        "STR_MODE_ENCRYPT_DISPLAY": "Encryption",
        "STR_MODE_DECRYPT_DISPLAY": "Decryption",
        "STR_DROP_FILE_ENCRYPT": "Drop Files or Folders for Encryption", 
        "STR_DROP_FILE_DECRYPT": "Drop ONE .age File for Decryption", 
        "STR_DROP_KEY_PUBLIC": "Recipient key needed! \n \n ( Drag and drop one or more public keys ) \n \n",
        "STR_DROP_KEY_PRIVATE": "Identity key needed! \n \n ( Drag and drop one private key ) \n \n ",
        "STR_DROP_FINISHED": "Finished %s",
        "STR_DROP_ERROR": "Failed: %s",
    }

    def __init__(self):
        super().__init__()

        # 1. Theme initialization
        self.is_dark_mode = darkdetect.isDark()
        self.colors = DARK_THEME_COLORS if self.is_dark_mode else LIGHT_THEME_COLORS
        self.strings = self.STRINGS

        self.setWindowTitle(self.strings["STR_TITLE"])
        
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
        
        self.btn_clear_keys = QPushButton(self.strings["STR_BTN_CLEAR_KEYS"], objectName="ClearKeysBtn")
        self.btn_clear_keys.clicked.connect(self._clear_keys_action)
        self.btn_clear_keys.setFixedSize(100, 28)
        footer_layout.addWidget(self.btn_clear_keys) 

        self.status_label = QLabel(self.strings["STR_STATUS_READY"] % "0", alignment=Qt.AlignVCenter)
        self.status_label.setFont(QFont("Arial", 10))
        self.status_label.setStyleSheet(f"color: {self.colors['TEXT_SECONDARY']};")
        footer_layout.addWidget(self.status_label, 1) 
        
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

        # After resetting, DropTarget will prompt you using the default encryption mode.
        self.drop_target.set_mode("file") 

        if clear_keys:
            self.recipients_keys = [] 

        key_status = str(len(self.recipients_keys))
        self.status_label.setText(self.strings["STR_STATUS_READY"] % key_status)

    def _clear_keys_action(self):
        if not self.recipients_keys:
            self.status_label.setText(self.strings["STR_STATUS_READY"] % "0")
            return

        reply = QMessageBox.question(
            self, 
            self.strings["STR_BTN_CLEAR_KEYS"], 
            self.strings["STR_CONFIRM_CLEAR_KEYS"], 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No 
        )

        if reply == QMessageBox.Yes:
            self.recipients_keys = []
            self._save_key_settings([], False) 

            self.keys = []

            if self._key_pending:
                self._reset_state_ui(clear_keys=False) 

            self.status_label.setText(self.strings["STR_STATUS_READY"] % "0")

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
        
    def _get_files_recursive(self, paths):
        """
        Recursively traverse the path and collect all files.
        """
        file_list = []
        for path in paths:
            if os.path.basename(path).startswith('.'):
                continue
                
            if os.path.isfile(path):
                file_list.append(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file_name in files:
                        if not file_name.startswith('.'):
                            file_list.append(os.path.join(root, file_name))
        return file_list

    def _on_files_dropped(self, paths):
        """
        Handles drag-and-drop files/folders.
        paths: Contains a list of top-level paths (files or folders) dragged in by the user.
        """
        if self._key_pending: return

        # 1. Preliminary pattern assessment (prioritize determining if it's for decryption)
        has_age_files = any(p.lower().endswith(".age") for p in paths)
        is_decrypt_mode = has_age_files or all(os.path.isfile(p) and p.lower().endswith(".age") for p in paths)
        
        # 2. **Decryption Mode Restriction Check (YubiKey Security Restriction)**
        if is_decrypt_mode:
            # Only a single file can be dragged in; folders and multiple files are not allowed.
            if len(paths) > 1 or os.path.isdir(paths[0]):
                self.drop_target.set_mode("error", self.strings["STR_ERROR_DECRYPT_MULTI"])
                self.status_label.setText(self.strings["STR_STATUS_ERROR_MIXED"])
                return
            
            # Make sure the single file you drag in is a .age file.
            if not paths[0].lower().endswith(".age") or not os.path.isfile(paths[0]):
                self.drop_target.set_mode("error", "The file must be a single .age file.")
                self.status_label.setText(self.strings["STR_STATUS_ERROR_MIXED"])
                return

            self.files_to_process = paths
            self.current_action_mode = "decrypt"
            
        else:
            # 3. Encryption mode (batch processing allowed)
            collected_files = self._get_files_recursive(paths)
            
            if not collected_files:
                self.drop_target.set_mode("error", "No valid files found for encryption.")
                self.status_label.setText(self.strings["STR_STATUS_ERROR_MIXED"])
                return
            
            # Check for the presence of .age files
            if any(p.lower().endswith(".age") for p in collected_files):
                self.drop_target.set_mode("error", self.strings["STR_ERROR_MIXED_FILES"])
                self.status_label.setText(self.strings["STR_STATUS_ERROR_MIXED"])
                return

            self.files_to_process = collected_files
            self.current_action_mode = "encrypt"


        # 4. Proceed to the next step according to the pattern.
        total_files = len(self.files_to_process)
        
        if self.current_action_mode == "decrypt":
            # Decrypt Mode: File check complete, next step requires key.
            self._key_pending = True
            # Users will need to pay attention to the CLI interface (where YubiKey prompts will appear).
            self.drop_target.set_mode("key", f"{self.strings['STR_DROP_KEY_PRIVATE']} After drop: Check console window")
            self.status_label.setText(self.strings["STR_STATUS_DECRYPT_MODE"])
        else:
            # Encrypt Mode
            if not self.recipients_keys: 
                # Require public key
                self._key_pending = True
                self.drop_target.set_mode("key", f"{self.strings['STR_DROP_KEY_PUBLIC']} ({total_files} files)")
                self.status_label.setText(self.strings["STR_STATUS_ENCRYPT_MODE"])
            else:
                # Start directly using the stored public key.
                self.keys = list(self.recipients_keys)
                self.status_label.setText(f"{self.strings['STR_STATUS_LOADED_KEYS'] % len(self.keys)} {self.strings['STR_STATUS_START_PROCESS'] % 'encrypt'} ({total_files} files)")
                self._start_process()

    def _on_keys_dropped_in_key_mode(self, paths):
        if not self._key_pending: return

        valid_key_paths = [p for p in paths if os.path.exists(p) and os.path.isfile(p)] 

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
            total_files = len(self.files_to_process)
            self.status_label.setText(f"{self.strings['STR_STATUS_LOADED_KEYS'] % len(self.recipients_keys)} {self.strings['STR_STATUS_START_PROCESS'] % 'encrypt'} ({total_files} files)")
        elif self.current_action_mode == "decrypt":
            self.status_label.setText(f"{self.strings['STR_STATUS_LOADED_KEYS'] % len(self.keys)} {self.strings['STR_STATUS_START_PROCESS'] % 'decrypt'} (1 file)")

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
            self.drop_target.set_mode("error", self.strings["STR_STATUS_ERROR_MIXED"])
            self.status_label.setText(self.strings["STR_STATUS_ERROR_MIXED"])
            self._reset_state_ui(clear_keys=False) 
            
        elif success == total:
            if self.current_action_mode == 'encrypt':
                mode_text_display = self.strings["STR_MODE_ENCRYPT_DISPLAY"]
                key_count = len(self.recipients_keys) 
            else:
                mode_text_display = self.strings["STR_MODE_DECRYPT_DISPLAY"]
                key_count = 0 

            self.drop_target.set_mode("finished", mode_text_display)
            self.status_label.setText(self.strings["STR_STATUS_FINISHED_KEYS"] % key_count)
            
            if self.current_action_mode == "decrypt":
                self.files_to_process = []
                self.keys = []
            
        else:
            error_count = total - success
            self.drop_target.set_mode("error", self.strings["STR_ERROR_FILES_FAIL"] % error_count)
            self.status_label.setText(self.strings["STR_STATUS_ERROR_MIXED"])
            self._reset_state_ui(clear_keys=False) 


if __name__ == "__main__":
    if os.name == 'nt':
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
