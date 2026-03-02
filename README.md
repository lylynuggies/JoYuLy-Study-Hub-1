# JoYuLy Study Hub

JoYuLy Study Hub is a FastAPI web app that helps students:
- upload papers and track progress/mastery
- generate study plans for upcoming exams
- run practice modes (tutorial/exam practice and on-the-go recap)
- authenticate with Firebase
- store app data in Firebase Firestore + Firebase Storage

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
|-- main.py
|-- requirements.txt
`-- testbench/
```

## Dependencies
Install all dependencies from:
- `requirements.txt`

## Prerequisites
1. Python 3.10 or newer
1. Firebase project with:
   - Authentication (Email/Password enabled)
   - Firestore Database
   - Storage bucket
1. Firebase Admin service account JSON downloaded locally
1. OpenAI API key (required)

## Environment Variables
Set these before running:

```env
FIREBASE_SERVICE_ACCOUNT_JSON=C:\absolute\path\to\your-firebase-adminsdk.json
OPENAI_API_KEY=your_openai_api_key
```

Notes:
- Only these 2 variables are required for normal setup.
- Firebase project id and bucket are auto-derived from your service account JSON.
- Firebase Web app config is prefilled in code for this project.
- Do not commit service account JSON to GitHub.

## Setup (Local)
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
1. Set environment variables (PowerShell example):
   ```powershell
   $env:FIREBASE_SERVICE_ACCOUNT_JSON="C:\absolute\path\to\your-firebase-adminsdk.json"
   $env:OPENAI_API_KEY="<REQUIRED_OPENAI_API_KEY>"
   ```
1. Run app:
   ```powershell
   py main.py
   ```
1. Open:
   - `http://127.0.0.1:8000`

## How to Use
1. Login/Register with Firebase auth page.
1. Go to Study Tracker:
   - upload paper
   - answer questions
   - submit for marking
1. Go to Reports:
   - view concept summary/question breakdown
   - download report file/PDF
1. Go to Study Plan:
   - add exams and topics
   - view priorities and predicted hours
   - generate tutorial/exam practice or recap quiz

## Testbench
See:
- `testbench/SETUP_AND_RUN.md`
- `testbench/TEST_CHECKLIST.md`

## GitHub Submission Steps
1. Create a new public GitHub repository.
1. In project root:
   ```powershell
   git init
   git add .
   git commit -m "Initial submission: JoYuLy Study Hub"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
1. Share the public repository link with judges.

## Security Notes
- Never commit credentials (`*.json` service account files, API keys).
- Use environment variables for secrets.

## Firebase Key Setup (Step-by-Step)
1. Go to Firebase Console and create/select your project.
1. In `Build > Authentication`, enable `Email/Password`.
1. In `Build > Firestore Database`, create database.
1. In `Build > Storage`, create bucket.
1. In `Project settings > General`, create a Web app if needed and copy:
   - `apiKey`
   - `authDomain`
   - `projectId`
   - `storageBucket`
   - `messagingSenderId`
   - `appId`
   (Only needed if you want to override default web config in code.)
1. In `Project settings > Service accounts`, generate a new private key JSON and store it locally.
1. Set the environment variables above and restart server.
