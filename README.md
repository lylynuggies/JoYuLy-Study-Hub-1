# JoYuLy Study Hub

JoYuLy Study Hub is a FastAPI web app that helps students:
- upload papers and track progress/mastery
- generate study plans for upcoming exams
- run practice modes (tutorial/exam practice and on-the-go recap)
- authenticate with Firebase
- store app data in Firebase Firestore + Firebase Storage

## Setup Checklist
1. Install Python 3.10+
1. Create Firebase project + enable Auth/Firestore/Storage
1. Download Firebase Admin service-account JSON
1. Get Firebase Web `apiKey`
1. Get OpenAI API key
1. Set 3 environment variables
1. Run `py main.py`

## Tech Stack
- Python 3.10+
- FastAPI
- Jinja2 templates
- Firebase Admin SDK (Firestore + Storage)
- OpenAI API (required for AI extraction/grading/question generation)

## Project Structure
```text
.
|-- app/
|   |-- main.py
|   |-- routes_*.py
|   |-- services.py
|   |-- firebase_backend.py
|   `-- ...
|-- templates/
|-- static/
|-- testbench/
|-- main.py
|-- requirements.txt
`-- .env.example
```

## Prerequisites
1. Python 3.10 or newer
1. Firebase project with:
   - Authentication (Email/Password enabled)
   - Firestore Database
   - Storage bucket
1. Firebase Admin service account JSON downloaded locally
1. OpenAI API key

## Required Environment Variables
Only these 3 variables are required:

```env
FIREBASE_SERVICE_ACCOUNT_JSON=C:\absolute\path\to\your-firebase-adminsdk.json
FIREBASE_WEB_API_KEY=your_firebase_web_api_key
OPENAI_API_KEY=your_openai_api_key
```

What each variable is for:
- `FIREBASE_SERVICE_ACCOUNT_JSON`: backend Firebase Admin authentication
- `FIREBASE_WEB_API_KEY`: frontend Firebase Auth initialization
- `OPENAI_API_KEY`: AI extraction, grading, and question generation

Why this setup?
- Firebase backend settings are auto-derived from your service-account JSON.
- Firebase `projectId`, `authDomain`, and `storageBucket` are auto-derived from service-account JSON.
- Firebase web API key is **not hardcoded**.

## Setup (Step-by-Step)
1. Open terminal in project root.
1. Create virtual environment:
   ```powershell
   py -m venv .venv
   ```
1. Activate:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
1. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
1. Set environment variables (PowerShell):
   ```powershell
   $env:FIREBASE_SERVICE_ACCOUNT_JSON="C:\absolute\path\to\your-firebase-adminsdk.json"
   $env:FIREBASE_WEB_API_KEY="your_firebase_web_api_key"
   $env:OPENAI_API_KEY="your_openai_api_key"
   ```
1. Run app:
   ```powershell
   py main.py
   ```
1. Open:
   - `http://127.0.0.1:8000`

## Common First-Run Mistakes
- Wrong JSON path in `FIREBASE_SERVICE_ACCOUNT_JSON`
- Forgetting to enable Email/Password in Firebase Auth
- Missing `FIREBASE_WEB_API_KEY`
- Not activating virtual environment before running install/app

## Firebase Setup (First Time Only)
1. Go to Firebase Console and create/select your project.
1. In `Build > Authentication`, enable `Email/Password`.
1. In `Build > Firestore Database`, create database.
1. In `Build > Storage`, create bucket.
1. In `Project settings > Service accounts`, generate a new private key JSON.
1. Save that JSON locally and set `FIREBASE_SERVICE_ACCOUNT_JSON` to that file path.
1. In `Project settings > General > Your apps > Web app`, copy `apiKey` into `FIREBASE_WEB_API_KEY`.

## How to Use
1. Login/Register from auth page.
1. Study Tracker:
   - upload `.pdf/.docx/.txt`
   - answer questions
   - submit for AI marking
1. Reports:
   - review concept summary/question breakdown
   - download report file/PDF
1. Study Plan:
   - add exam date + topics
   - view priorities and predicted hours
   - generate tutorial/exam practice or recap quiz

## Testbench
For judging/testing:
- `testbench/SETUP_AND_RUN.md`
- `testbench/TEST_CHECKLIST.md`
- `testbench/FILES_REQUIRED.md`

## Troubleshooting
- Firebase login/admin errors:
  - confirm `FIREBASE_SERVICE_ACCOUNT_JSON` path is correct
  - confirm Firebase services (Auth/Firestore/Storage) are enabled
- Upload/report errors:
  - check service account permissions for Firestore and Storage
- OpenAI-related errors:
  - confirm `OPENAI_API_KEY` is set and valid

## Security Notes
- Never commit credentials (`*.json` service account files or API keys).
- Keep secrets in environment variables only.
