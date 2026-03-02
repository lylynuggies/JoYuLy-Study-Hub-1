# Testbench: Setup and Run Guide

This document provides step-by-step instructions for judges/testers.

## 1) Clone Repository
```powershell
git clone https://github.com/<owner>/<repo>.git
cd <repo>
```

## 2) Create and Activate Virtual Environment
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3) Install Dependencies
```powershell
pip install -r requirements.txt
```

## 4) Configure Environment Variables
Required:
```powershell
$env:FIREBASE_SERVICE_ACCOUNT_JSON="C:\absolute\path\to\your-firebase-adminsdk.json"
$env:FIREBASE_PROJECT_ID="your_project_id"
$env:FIREBASE_STORAGE_BUCKET="your_project_bucket"
$env:FIREBASE_WEB_API_KEY="your_web_api_key"
$env:FIREBASE_WEB_AUTH_DOMAIN="your_project.firebaseapp.com"
$env:FIREBASE_WEB_PROJECT_ID="your_project_id"
$env:FIREBASE_WEB_STORAGE_BUCKET="your_project_bucket"
$env:FIREBASE_WEB_MESSAGING_SENDER_ID="your_messaging_sender_id"
$env:FIREBASE_WEB_APP_ID="your_web_app_id"
$env:OPENAI_API_KEY="sk-..."
```

Notes:
- Use your own Firebase project values for all Firebase variables.

## 5) Run App
```powershell
py main.py
```

Open:
- `http://127.0.0.1:8000`

## 6) Quick Functional Run
1. Login/register through Firebase page.
1. Navigate to `Study Tracker`.
1. Upload `.pdf/.docx/.txt` file.
1. Open generated paper bank and submit at least one answer.
1. Open report page and test PDF/report downloads.
1. Navigate to `Study Plan`, add exam data, generate practice modes.

## 7) Troubleshooting
- Firebase Admin credential errors:
  - Confirm `FIREBASE_SERVICE_ACCOUNT_JSON` path is valid.
  - Confirm service account has Firestore/Storage permissions.
- Storage upload failures:
  - Verify `FIREBASE_STORAGE_BUCKET` value.
- AI-related issues:
  - Confirm `OPENAI_API_KEY` is set correctly.

## 8) How to Get Firebase Keys
1. Firebase Console -> Project settings -> General -> Your apps -> Web app config.
1. Copy values into:
   - `FIREBASE_WEB_API_KEY`
   - `FIREBASE_WEB_AUTH_DOMAIN`
   - `FIREBASE_WEB_PROJECT_ID`
   - `FIREBASE_WEB_STORAGE_BUCKET`
   - `FIREBASE_WEB_MESSAGING_SENDER_ID`
   - `FIREBASE_WEB_APP_ID`
1. Firebase Console -> Project settings -> Service accounts -> Generate new private key.
1. Save JSON locally and set `FIREBASE_SERVICE_ACCOUNT_JSON` to that file path.
