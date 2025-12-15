![ScreenShot](https://github.com/louischang38/yubiage_ui/blob/main/screenshot/screenshot.png)
# YubiAge UI

**Age File Encryption / Decryption with YubiKey GUI Tool**

A simple, cross-platform Graphical User Interface (GUI) built with PySide6 for handling file encryption and decryption using the Age encryption tool.  

This application simplifies the drag-and-drop workflow, especially for users managing keys from YubiKey devices or standard Age key files.

---

## Features

- **Drag-and-Drop Interface**  
  Encrypt or decrypt files by dragging them into the main window.

- **Automatic Mode Detection**  
  Automatically detects Encrypt / Decrypt mode based on the dropped file type.

- **Key Management**  
  Supports dropping recipient public keys (for encryption) or identity private keys (for decryption).

- **Key Persistence (Encryption)**  
  Remembers the last used recipient keys during encryption sessions.

- **Cross-Platform**  
  Windows / macOS / Linux


## Decryption Design Limitation

Due to the behavior of the `age` CLI and YubiKey-based decryption mechanisms, each decryption operation requires an independent verification and authorization step.

Specifically:

- The `age` command-line tool prompts for confirmation or key access on every decryption request.
- YubiKey-backed identities require a physical user presence (touch / PIN / confirmation) for each operation.

To avoid unintended CLI behavior, authorization confusion, or user interaction errors during batch processing, the decryption feature is intentionally designed to operate on **a single file at a time**.

This design ensures:

- Clear and predictable authorization flow
- Reduced risk of accidental or failed decryption operations
- Better alignment with the security model of hardware-backed keys

As a result, bulk decryption is intentionally not supported.
---



## Prerequisites

The following command-line tools must be installed and available in your system `PATH`.

**Required:**

- [age (Age Encryption Tool)](https://github.com/FiloSottile/age)
- [age-plugin-yubikey](https://github.com/str4d/age-plugin-yubikey)  

**Optional (Hardware / Secure Element Support):**
- [age-plugin-se (macOS Secure Enclave)](https://github.com/remko/age-plugin-se)

---

## Installation and Usage

### Option 1: Running the Application (Executable)  
*Recommended for end users.*

1. Download the latest compiled executable from the Releases page:  
   - Windows: `.exe`  
   - macOS / Linux: binary

2. Run the application directly. No Python installation required.

### Option 2: Running from Source (Python Script)  
*For developers or advanced users.*

1. Download the main script:  
   `yubiage_ui.py`

2. Install dependencies:
pip install PySide6
pip install darkdetect

3. Run the application:
python yubiage_ui.py

4. Alternatively, you can build the executable yourself with PyInstaller:

**Windows:**
python -m PyInstaller --onefile --windowed --name "yubiage_ui" --icon "icon.ico" --add-data "icon.ico;." --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui --hidden-import PySide6.QtWidgets --exclude-module PySide6.QtWebEngine --exclude-module PySide6.QtNetwork --exclude-module PySide6.QtMultimedia --exclude-module PySide6.QtSql --exclude-module PySide6.QtTest --clean yubiage_ui.py

**macOS:**
python -m PyInstaller --onedir --console --windowed --name "yubiage_ui" --icon "icon.icns" --add-data "icon.icns:." --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui --hidden-import PySide6.QtWidgets --exclude-module PySide6.QtWebEngine --exclude-module PySide6.QtNetwork --exclude-module PySide6.QtMultimedia --exclude-module PySide6.QtSql --exclude-module PySide6.QtTest --clean yubiage_ui.py

---

## How to Use

### Encryption
1. Drag one or more **non-.age files** into the main window. The application switches to **Key Mode** automatically.  
2. Drag the recipient **public key** (starts with `age`) into the window.  
3. Each file is encrypted and saved with a `.age` extension.

### Decryption
1. Drag one or more **.age files** into the main window. The application switches to **Key Mode** automatically.  
2. Drag the **identity private key** into the window.  
3. Files are decrypted

---

# 中文說明

## YubiAge GUI（Age 檔案加解密工具）

YubiAge GUI 是一個基於 PySide6 的簡潔、跨平台圖形使用者介面（GUI），用於透過 Age 加密工具進行檔案加密與解密。  

本工具以拖放操作為核心設計，特別適合使用 **YubiKey 硬體金鑰** 或標準 Age 金鑰檔案的使用者。

---

## 專案特色

- **拖放介面**  
  將檔案拖放至主視窗即可完成加解密

- **模式自動判斷**  
  依據檔案類型自動切換加密或解密模式

- **金鑰管理**  
  支援拖放收件人公鑰（加密）與身份私鑰（解密）

- **金鑰記憶功能（加密）**  
  自動記住上次使用的收件人金鑰

- **跨平台支援**  
  Windows / macOS / Linux


## 解密功能設計限制說明

由於 `age` 指令列工具與 YubiKey 硬體金鑰在進行解密時，
**每一次解密操作都需要獨立的驗證與授權流程**（例如 PIN 輸入、實體觸碰或使用者確認），
因此本工具在解密功能的設計上，**僅支援單一檔案解密**。

主要考量如下：

- `age` CLI 每次解密皆會觸發獨立的金鑰存取與驗證
- YubiKey 解密操作必須逐次進行實體授權
- 批次解密容易造成 CLI 操作混亂或授權錯誤

為避免因批次操作導致誤解密、授權失敗或不可預期的行為，
解密流程刻意限制為 **一次僅處理一個檔案**。

此設計可確保：

- 驗證流程清楚可控
- 降低操作失誤與安全風險
- 符合硬體金鑰的安全模型

因此，本工具**暫時不支援批次解密功能**。
---



## 系統需求

系統中必須安裝以下命令列工具，並可於 PATH 中存取：

**必要：**

- age  
  [GitHub](https://github.com/FiloSottile/age)
- age-plugin-yubikey  

**選用（硬體金鑰 / Secure Enclave）：**
- age-plugin-se（macOS）

---

## 安裝與執行

### 選項一：使用編譯後的執行檔（推薦）
1. 從 Releases 頁面下載最新版本  
2. 直接執行即可使用（無需 Python 安裝）

### 選項二：從原始碼執行（Python）
1. 下載主程式  
   `yubiage_ui.py`

2. 安裝依賴
pip install PySide6
pip install darkdetect

3. 執行
python yubiage_ui.py

4. 或使用 PyInstaller 自行編譯執行檔

**Windows:**
python -m PyInstaller --onefile --windowed --name "yubiage_ui" --icon "icon.ico" --add-data "icon.ico;." --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui --hidden-import PySide6.QtWidgets --exclude-module PySide6.QtWebEngine --exclude-module PySide6.QtNetwork --exclude-module PySide6.QtMultimedia --exclude-module PySide6.QtSql --exclude-module PySide6.QtTest --clean yubiage_ui.py

**macOS:**
python -m PyInstaller --onedir --console --windowed --name "yubiage_ui" --icon "icon.icns" --add-data "icon.icns:." --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui --hidden-import PySide6.QtWidgets --exclude-module PySide6.QtWebEngine --exclude-module PySide6.QtNetwork --exclude-module PySide6.QtMultimedia --exclude-module PySide6.QtSql --exclude-module PySide6.QtTest --clean yubiage_ui.py

---

## 使用方式

### 加密
1. 拖放一個或多個 **非 .age 檔案** 至主視窗  
   程式自動切換至 **金鑰模式**

2. 拖放收件人 **公鑰**（age 開頭）  

3. 產生對應的 `.age` 加密檔案

### 解密
1. 拖放一個或多個 **.age 檔案**  
   程式自動切換至 **金鑰模式**

2. 拖放 **身份私鑰**  

3. 解密完成
