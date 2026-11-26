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

## Build the Windows app

Build the windowed, one-folder app (the existing `.build-venv` must have the packages in `requirements-build.txt`):

```powershell
.\build.ps1
```

The builder does not install packages or use the system temporary directory. Build intermediates, PyInstaller's cache, and the log stay under this repository's `build\` folder. The executable and its support files are created under `dist\WilsonDogSelfHelp\`; keep that whole folder together. This one-folder build avoids PyInstaller's one-file runtime extraction to a temporary folder. Run the executable once to enable launch when you sign in to Windows. The packaged app has a **Start Wilson when I sign into Windows** setting you can turn off. Running `app.py` during development does not change startup settings.

Close the running executable before rebuilding. Persistent build intermediates and the PyInstaller log stay under `build\`; the detailed log is `build\pyinstaller-output.log`.

Wilson uses a per-user Windows startup entry and a Windows mutex for single-instance behavior. It doesn't create a lock file.

## Prototype features

- Add your own daily tasks and give each one a time limit (in minutes). A countdown shows how long is left, and the task is flagged as overdue once time runs out.
- Confirm a task before it is marked complete. Completed tasks are crossed out and cannot be completed again that day.
- The dog's mood slowly fades during the day. Finishing tasks raises it; finishing all tasks sets it to 100% until the next day.
- Open **Settings** (below the task list) to choose the dog's name, temperament, and icon, and the Windows sign-in startup option.
- Resize the widget by dragging its bottom-right corner; the size is remembered.
- Minimize the widget down to its title bar with the – button, and expand it again with +.
- Switch between light and dark mode with the ☾ / ☀ button.
- Settings, tasks, time limits, and mood are saved locally. Task completion, task countdowns, and mood reset each new day.

The temperament choices currently use placeholder lines. Custom sprite art and richer dialogue can be added later.
