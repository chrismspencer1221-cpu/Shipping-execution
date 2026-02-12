# Shipping Execution Desktop (Windows)

This is a desktop tool (runs locally in your browser) to execute your KC shipping outreach plan.

## What it does
- Import your Excel/CSV targets
- Shows Dashboard + Due Today
- Target detail: review email, then open Outlook (review-first), then log touch
- Cadence engine auto-schedules next action
- Template editor
- Export targets/touches and optional HubSpot tasks CSV

## Install (one-time)
1) Install Python 3.10+ (Windows)
2) Open Command Prompt in this folder
3) Run:
   pip install -r requirements.txt

## Run
Double-click `run_windows.bat`
(or run: python -m streamlit run app.py)

## Email
This uses a `mailto:` link to open your default email client.
Set Outlook as your Windows default mail app for best results.

## Import format
At minimum, your file must have columns:
- Company
- Domain

Optional columns:
- Target Role
- Contact Name
- Email / Pattern (or Email Pattern or Email)

Tip: Use the KC_Targets_1_50.xlsx you already have and import it directly.
