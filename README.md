YubiAge GUI (Age File Encryption/Decryption with YibiKey GUI Tool)
A simple, cross-platform Graphical User Interface (GUI) built with PySide6 for handling file encryption and decryption using the Age encryption tool.
This application simplifies the drag-and-drop process for end-users, especially when managing keys from YubiKey devices or standard key files.

=======================================================================================================================================================

Features
Drag-and-Drop Interface: Easily encrypt or decrypt files by dropping them onto the main window.
Automatic Mode Detection: Automatically detects the operation mode (Encrypt/Decrypt) based on the dropped file type.
Key Management: Supports dropping recipient keys (for encryption) or identity keys (for decryption).
Key Persistence (Encryption): Remembers the last used recipient keys for encryption sessions 

=======================================================================================================================================================

Installation and Usage

Prerequisites:
You need to have the age command-line tool installed on your system.

*** This application relies on the following command-line tools to be installed and accessible in your system's PATH.  ***

[Installation instructions for Age Tool]: Refer to the official Age repository for installation tailored to your OS (Windows, macOS, Linux).
https://github.com/FiloSottile/age

Install Plugins: Install necessary plugins like age-plugin-yubikey and age-plugin-se if you intend to use hardware security modules.

https://github.com/str4d/age-plugin-yubikey
https://github.com/remko/age-plugin-se



Option 1: Running the Application (Executable)
This method is recommended for end-users.
Download: Download the latest compiled executable (.exe, or binary) from the Releases section.

Run: Simply execute the application file.

Option 2: Running from Source (Python Script)
This method is for developers or users who prefer to run the script directly.

1.download the ageyubi.py
2.Install dependencies
  pip install PySide6
  pip install  darkdetect
3.python ageyubi.py

=======================================================================================================================================================

How to Use
Encryption:
Drop one or more files (not .age files) onto the main window.
The application will switch to Key Mode. Drop the recipient public key (age... key) onto the window.
The files will be encrypted, resulting in a .age file for each input file.

Decryption:
Drop one or more .age files onto the main window.
The application will switch to Key Mode. Drop the identity private key (used for decryption) onto the window.
The files will be decrypted, removing the .age extension.





YubiAge GUI (Age 檔案加解密工具)
這是一個基於 PySide6 建構的簡潔、跨平台的圖形使用者介面（GUI）應用程式，旨在利用 Age 加密工具處理檔案的加解密操作。

本應用程式簡化了拖放流程，特別適用於管理來自 YubiKey 裝置或標準金鑰檔案的使用者。

✨ 專案特色
拖放介面： 透過將檔案拖放到主視窗，輕鬆完成加解密操作。
模式自動偵測： 根據拖放檔案的類型，自動判斷應執行加密或解密模式。
金鑰管理： 支援拖放收件人金鑰（用於加密）或身份金鑰（用於解密）。
金鑰記憶（加密）： 會記住上次用於加密會話的收件人金鑰。


安裝與使用
前提條件

您的系統上必須安裝有 age 命令列工具及age-plugin-yuibi, 在mac上也可以加上 age-plugin-se 。
[Age 工具安裝說明]：請參考 Age 官方儲存庫獲取適用於您作業系統（Windows、macOS、Linux）的安裝指南。



選項 1: 執行應用程式 (執行檔)
此方法推薦給一般終端使用者。

下載： 從 Release 頁面下載最新的編譯執行檔（例如 .exe 或 二進位執行檔）。
運行： 直接執行應用程式檔案。


選項 2: 從源碼運行 (Python 腳本)
此方法適用於開發人員或偏好直接執行腳本的使用者。

1.下戴phthon主檔：  
     ageyubi.py
     
2.安裝依賴 (使用 pip)：
  pip install PySide6
  pip install  darkdetect
  
3.執行 Python 腳本
  python ageyubi.py


使用方法
加密：
將一個或多個檔案（非 .age 檔案）拖放到主視窗。
應用程式將切換到金鑰模式。將收件人的公鑰（age... 開頭的金鑰）拖放到視窗中。
檔案將被加密，每個輸入檔案都會生成一個 .age 檔案。

解密：
將一個或多個 .age 檔案拖放到主視窗。
應用程式將切換到金鑰模式。將身份私鑰（用於解密的金鑰）拖放到視窗中。
檔案將被解密，並移除 .age 副檔名。


  
