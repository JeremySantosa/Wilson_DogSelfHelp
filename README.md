# Wilson_DogSelfHelp

Wilson is a self-care Windows widget that gamifies completion of user-set tasks into a pet caring experience.

## Daily Dog prototype

A tiny desktop pet prototype built with Python and PySide6. It stays above other windows, can be dragged, and reacts to three sample daily goals.

### Run on Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py app.py
```

The goals and checked state are currently sample data and reset whenever the app closes. This first version is meant to test the daily interaction and pet feedback before adding persistence, reminders, or packaging.
