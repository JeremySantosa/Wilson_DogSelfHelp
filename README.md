# Author
Jeremy William Santosa

# Wilson_DogSelfHelp

Wilson is a self-care Windows widget that gamifies completion of user-set tasks into a pet caring experience.

## Run on Windows

Install dependencies once:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the widget whenever you like:

```powershell
.\.venv\Scripts\python.exe app.py
```

Run these commands from the repository folder. The widget stays above other windows and can be dragged by its title bar.

## Build the Windows executable

Build the single-file, windowed executable:

```powershell
.\build.ps1
```

The script creates a separate `.build-venv`, installs the build requirements, and creates `dist\WilsonDogSelfHelp.exe`. Run the executable once to enable launch when you sign in to Windows. The packaged app has a **Start Wilson when I sign into Windows** setting you can turn off. Running `app.py` during development does not change startup settings.

Wilson uses a per-user Windows startup entry and a lock file in its app-data folder, so it starts for your account and prevents a second copy from opening.

## Prototype features

- Add your own daily tasks and choose a deadline time for each one.
- Confirm a task before it is marked complete. Completed tasks are crossed out and cannot be completed again that day.
- The dog's mood slowly fades during the day. Finishing tasks raises it; finishing all tasks sets it to 100% until the next day.
- Choose the dog's name, temperament, and emoji style.
- Settings, tasks, deadlines, and mood are saved locally. Task completion and mood reset each new day.

The temperament choices currently use placeholder lines. Custom sprite art and richer dialogue can be added later.
