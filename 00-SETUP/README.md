# KERI Setup (Windows)

This guide explains how to properly install and activate KERI (keripy) in a Python environment on Windows.

---

## Prerequisites

- Windows 10/11  
- Python 3.13 installed (for KERI >= 1.0.4)  
- Git installed  
- PowerShell or Command Prompt  
- Internet connection to download Python packages

---

## Step 1 — Checking Python Version 

KERIPY requires Python >= 3.13.  

```powershell
python --version
````

---

## Step 2 — Create a Python Virtual Environment

Use your installed Python 3.13:

```powershell
python -m venv keri-env
```

Activate the environment:

```powershell
.\keri-env\Scripts\Activate.ps1
```

Confirm Python and pip versions:

```powershell
python --version
pip --version
```

Upgrade pip, setuptools, wheel:

```powershell
pip install --upgrade pip setuptools wheel
```

---

## Step 3 — Install KERIPY from GitHub

```powershell
pip install git+https://github.com/WebOfTrust/keripy.git
```

---

## Step 4 — Install libsodium (Required for pysodium)

1. Download prebuilt DLL from libsodium releases:

   * `libsodium-1.0.20-msvc.zip` or newer if it exists
2. Extract the zip and locate `libsodium.dll` (typically under `x64\Release\v143\dynamic\`)
3. Copy `libsodium.dll` to your virtual environment's Scripts folder:

```text
C:\Users\chari\Documents\GitHub\KERI-Blockchain-Anchored-IT-OT\keri-env\Scripts\
```

4. Verify it’s visible to Python:

```powershell
python .\test_libsodium.py
```

Expected output: path to `libsodium.dll`.

---

## Step 5 — Test KERI Import

Run:

```powershell
python .\test_keri.py
```

Expected output:

![01-keri-test](./attachments/01-keri-tesr.png)



## Or you can just — Use the Provided Virtual Environment from GitHub

The `keri-env` virtual environment has already been created and pushed to this repository.  
After cloning the repo, you can activate it directly:

```powershell
.\keri-env\Scripts\Activate.ps1
```
