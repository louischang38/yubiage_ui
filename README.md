YubiAge GUI
Age File Encryption / Decryption with YubiKey GUI Tool

A simple, cross-platform Graphical User Interface (GUI) built with PySide6 for handling file encryption and decryption using the Age encryption tool.

This application simplifies the drag-and-drop workflow, especially for users managing keys from YubiKey devices or standard Age key files.

FEATURES

Drag-and-Drop Interface
Encrypt or decrypt files by dragging them into the main window.

Automatic Mode Detection
Automatically detects Encrypt / Decrypt mode based on the dropped file type.

Key Management
Supports dropping recipient public keys (for encryption) or identity private keys (for decryption).

Key Persistence (Encryption)
Remembers the last used recipient keys during encryption sessions.

Cross-Platform
Windows / macOS / Linux

PREREQUISITES

The following command-line tools must be installed and available in your system PATH.

Required:

age (Age Encryption Tool)
https://github.com/FiloSottile/age

Optional (Hardware / Secure Element Support):

age-plugin-yubikey
https://github.com/str4d/age-plugin-yubikey

age-plugin-se (macOS Secure Enclave)
https://github.com/remko/age-plugin-se

INSTALLATION AND USAGE

Option 1: Running the Application (Executable)
Recommended for end users.

Download the latest compiled executable from the Releases page

Windows: .exe

macOS / Linux: binary

Run the application directly
No Python installation required.

Option 2: Running from Source (Python Script)
For developers or advanced users.

Download the main script
ageyubi.py

Install dependencies
pip install PySide6
pip install darkdetect

Run the application
python ageyubi.py

HOW TO USE

Encryption:

Drag one or more files (non-.age files) into the main window.

The application switches to Key Mode.

Drag the recipient public key (starts with "age") into the window.

Each file is encrypted and saved with a .age extension.

Decryption:

Drag one or more .age files into the main window.

The application switches to Key Mode.

Drag the identity private key into the window.

Files are decrypted and the .age extension is removed.

YubiAge GUI（Age 檔案加解密工具）

YubiAge GUI 是一個基於 PySide6 的簡潔、跨平台圖形使用者介面（GUI），
用於透過 Age 加密工具進行檔案加密與解密。

本工具以拖放操作為核心設計，特別適合使用 YubiKey 硬體金鑰
或標準 Age 金鑰檔案的使用者。

專案特色

拖放介面
將檔案拖放至主視窗即可完成加解密

模式自動判斷
依據檔案類型自動切換加密或解密模式

金鑰管理
支援拖放收件人公鑰（加密）與身份私鑰（解密）

金鑰記憶功能（加密）
自動記住上次使用的收件人金鑰

跨平台支援
Windows / macOS / Linux

系統需求

系統中必須安裝以下命令列工具，並可於 PATH 中存取：

必要：

age
https://github.com/FiloSottile/age

選用（硬體金鑰 / Secure Enclave）：

age-plugin-yubikey

age-plugin-se（macOS）

安裝與執行

選項一：使用編譯後的執行檔（推薦）

從 Releases 頁面下載最新版本

直接執行即可使用

選項二：從原始碼執行（Python）

下載主程式
ageyubi.py

安裝依賴
pip install PySide6
pip install darkdetect

執行
python ageyubi.py

使用方式

加密：

拖放一個或多個非 .age 檔案至主視窗

程式自動切換至金鑰模式

拖放收件人公鑰（age 開頭）

產生對應的 .age 加密檔案

解密：

拖放一個或多個 .age 檔案

程式自動切換至金鑰模式

拖放身份私鑰

解密完成並移除 .age 副檔名
