# JoYuLy Study Hub

JoYuLy Study Hub is a FastAPI web app for students to:
- upload papers and track progress/mastery
- generate study plans for upcoming exams
- run practice modes (tutorial/exam practice and on-the-go recap)
- authenticate with Firebase

## Quick Start (Beginner)
1. Install Python 3.10+.
1. Create a Firebase project and enable:
   - Authentication (Email/Password)
   - Firestore Database
   - Storage
1. Download your **Firebase Admin service account JSON**.
1. Get your **OpenAI API key**.
1. In this project folder, run:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
1. Set required environment variables:
   ```powershell
   $env:FIREBASE_SERVICE_ACCOUNT_JSON="C:\absolute\path\to\your-firebase-adminsdk.json"
   $env:OPENAI_API_KEY="your_openai_api_key"
   ```
1. Run:
   ```powershell
   py main.py
   ```
1. Open `http://127.0.0.1:8000`

## Why Only 2 Variables?
You only need:
- `FIREBASE_SERVICE_ACCOUNT_JSON`
- `OPENAI_API_KEY`

The app auto-derives Firebase backend project settings from your service-account JSON.  
Frontend Firebase web config is already prefilled in code for this project.

## Project Structure
```text
.
|-- app/
|-- templates/
|-- static/
|-- testbench/
|-- main.py
|-- requirements.txt
`-- .env.example
```

## Testbench
For judging/testing flow:
- `testbench/SETUP_AND_RUN.md`
- `testbench/TEST_CHECKLIST.md`

## Security Notes
- Never commit credentials (`*.json` service account files or API keys).
- Keep secrets in environment variables only.
