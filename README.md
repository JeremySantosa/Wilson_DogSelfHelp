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

## Prototype features

- Add your own daily tasks and choose a deadline time for each one.
- Confirm a task before it is marked complete. Completed tasks are crossed out and cannot be completed again that day.
- The dog's mood slowly fades during the day. Finishing tasks raises it; finishing all tasks sets it to 100% until the next day.
- Choose the dog's name, temperament, and emoji style.
- Settings, tasks, deadlines, and mood are saved locally. Task completion and mood reset each new day.

The temperament choices currently use placeholder lines. Custom sprite art and richer dialogue can be added later.
