# Control-Optimizer

# 🌍 Internationalization (i18n) Build

This project includes a PowerShell script to manage translations for the application using **PySide6**.

Languages are configured in `src/config/languages.json`. To add a new language, add its language code to the `languages` array in that JSON file. To remove a language, delete its code from the same array.

## 📌 Overview

The script:

- Scans the source code for translatable strings  
- Updates `.ts` translation files  
- Opens **Qt Linguist** if new strings are detected  
- Compiles `.qm` files for runtime use  
- Keeps translation files in sync with the configuration  

---

## ▶️ Usage

From the project root:


```powershell
cd src
.\i18n\build-i18n.ps1
```
