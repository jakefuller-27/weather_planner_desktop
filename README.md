# Jobsite Weather Planner

A Tkinter desktop app for checking a seven-day weather forecast for a jobsite.
It shows separate crane, concrete, and roofing ratings, explains the values
behind a selected rating, supports working-hour filters and city search, and
can save/open jobsite settings or export the forecast to CSV.

Forecast and city-search data come from Open-Meteo. An internet connection is
required.

## Install on macOS

Use Python 3 with Tkinter available, then create and activate a virtual
environment from the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project packages:

```bash
pip install tkintermapview requests
```

The same package list is in `requirements.txt`; it can also be installed with:

```bash
pip install -r requirements.txt
```

## Run the app

From the project directory, with the virtual environment activated:

```bash
python3 app.py
```

## Run validation

```bash
python3 validate.py
```

The validation script runs fixture, threshold, property, working-hours,
Provo geocoding, saved-jobsite, and CSV checks. Its live forecast and
geocoding checks need an internet connection; it also prints today's raw
West Jordan hourly forecast and calculated values.

## Project files

- `app.py` — Tkinter application and user interface.
- `calc.py` — forecast request helpers, daily aggregation, and activity ratings.
- `jobsites.py` — JSON save/open and validation for jobsite settings.
- `exports.py` — CSV generation.
- `validate.py` — automated fixture, feature, and live-data checks.
- `requirements.txt` — Python package dependencies.
- `spec.md` — application specification.
- `AGENTS.md` — project instructions.
- `prompts.md` — request and change history.
- `README.md` — setup, run, validation, and project-file guide.
