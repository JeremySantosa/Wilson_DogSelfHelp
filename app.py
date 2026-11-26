#The app itself
from __future__ import annotations

import html
import ctypes
import json
import math
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from ctypes import wintypes

from PySide6.QtCore import QStandardPaths, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


MOOD_DECAY_PER_HOUR = 2.0
ERROR_ALREADY_EXISTS = 183
DEFAULT_TASK_MINUTES = 60
MIN_WIDTH = 340
DEFAULT_WIDTH = 390
DEFAULT_HEIGHT = 560
TASKS_PAGE = 0
SETTINGS_PAGE = 1


def acquire_instance_mutex():
    """Return a held Windows mutex, or None if another instance owns it."""
    if sys.platform != "win32":
        return True

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_mutex = kernel32.CreateMutexW
    create_mutex.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    create_mutex.restype = wintypes.HANDLE
    ctypes.set_last_error(0)
    handle = create_mutex(None, True, r"Local\WilsonDogSelfHelp")
    error_code = ctypes.get_last_error()
    if not handle:
        raise ctypes.WinError(error_code)

    if error_code == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return kernel32, handle

TEMPERAMENT_MESSAGES = {
    "Kind": {
        "idle": "One step at a time. I believe in you.",
        "progress": "Nice progress! Keep going at your own pace.",
        "done": "You did it! I'm proud of you.",
    },
    "Sassy": {
        "idle": "The task list is not going to do itself, you know.",
        "progress": "Look at you, being all responsible.",
        "done": "Fine, that was pretty impressive.",
    },
}

# Colour palettes for the light and dark themes.
THEMES = {
    "light": {
        "card": "#fffaf0", "border": "#eadfca", "text": "#332d27",
        "muted": "#66594c", "faint": "#76695d", "input": "#fffdf8",
        "input_border": "#ded2c2", "popup_border": "#cbbba6",
        "accent": "#e9a86c", "accent_hover": "#f0b77f", "accent_text": "#30251c",
        "secondary": "#eee7dc", "secondary_text": "#30251c",
        "disabled": "#ded7cc", "disabled_text": "#756e64",
        "track": "#eee7dc", "good": "#91b887", "overdue": "#c0503a",
    },
    "dark": {
        "card": "#2a2521", "border": "#3e3630", "text": "#f2eadf",
        "muted": "#c8bbab", "faint": "#a89b8c", "input": "#352f2a",
        "input_border": "#4b423a", "popup_border": "#5a5047",
        "accent": "#e9a86c", "accent_hover": "#f0b77f", "accent_text": "#30251c",
        "secondary": "#443b34", "secondary_text": "#f2eadf",
        "disabled": "#3e3630", "disabled_text": "#8a7f74",
        "track": "#443b34", "good": "#91b887", "overdue": "#ef8a73",
    },
}


def build_stylesheet(p: dict) -> str:
    return f"""
        QFrame#card {{ background: {p['card']}; border: 1px solid {p['border']};
                      border-radius: 18px; }}
        QLabel {{ color: {p['text']}; }}
        QLabel#pet {{ font-size: 52px; }}
        QLabel#status {{ color: {p['muted']}; }}
        QLabel#timeLeft {{ color: {p['faint']}; font-size: 11px; }}
        QLabel#timeLeft[overdue="true"] {{ color: {p['overdue']}; font-weight: 700; }}
        QLineEdit, QComboBox, QSpinBox {{
            background: {p['input']}; border: 1px solid {p['input_border']};
            border-radius: 7px; padding: 6px; color: {p['text']};
        }}
        QComboBox QAbstractItemView {{
            background: {p['input']}; color: {p['text']};
            selection-background-color: {p['accent']};
            selection-color: {p['accent_text']}; border: 1px solid {p['popup_border']};
            outline: 0;
        }}
        QComboBox QAbstractItemView::item {{ min-height: 28px; padding: 4px 8px; }}
        QCheckBox {{ color: {p['text']}; }}
        QPushButton {{ background: {p['accent']}; color: {p['accent_text']}; border: 0;
                      border-radius: 8px; padding: 7px 10px; }}
        QPushButton:hover {{ background: {p['accent_hover']}; }}
        QPushButton:disabled {{ background: {p['disabled']}; color: {p['disabled_text']}; }}
        QPushButton#secondaryButton {{ background: {p['secondary']};
                                      color: {p['secondary_text']}; }}
        QMessageBox {{ background: {p['card']}; color: {p['text']}; }}
        QMessageBox QLabel {{ background: transparent; color: {p['text']}; }}
        QMessageBox QPushButton {{ background: {p['accent']}; color: {p['accent_text']};
                                  min-width: 78px; }}
        QMessageBox QPushButton:hover {{ background: {p['accent_hover']}; }}
        QFrame#taskRow {{ background: {p['input']}; border: 1px solid {p['border']};
                         border-radius: 10px; }}
        QProgressBar {{ background: {p['track']}; border: 0; border-radius: 6px;
                       height: 12px; text-align: center; }}
        QProgressBar::chunk {{ background: {p['good']}; border-radius: 6px; }}
        QScrollArea {{ border: 0; background: transparent; }}
        QScrollArea > QWidget > QWidget {{ background: transparent; }}
    """


def time_left_text(task: dict) -> tuple[str, bool]:
    """Return a short countdown label for a task and whether it is overdue."""
    if task.get("done"):
        return "done", False
    try:
        due = datetime.fromisoformat(task["due_at"])
    except (KeyError, TypeError, ValueError):
        return "", False
    seconds = (due - datetime.now()).total_seconds()
    if seconds <= 0:
        return "Overdue", True
    hours, minutes = divmod(math.ceil(seconds / 60), 60)
    if hours:
        return f"{hours}h {minutes:02d}m left", False
    return f"{minutes}m left", False


class DragBar(QWidget):
    """Small title bar that lets the frameless widget be dragged."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._drag_offset = None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None


class TaskRow(QFrame):
    complete_requested = Signal(str)
    remove_requested = Signal(str)

    def __init__(self, task: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.task_id = task["id"]
        self.setObjectName("taskRow")

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 8, 7)
        row.setSpacing(8)

        title = html.escape(task["title"])
        if task.get("done", False):
            title = f"<s>{title}</s>"
        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setTextFormat(Qt.TextFormat.RichText)
        row.addWidget(self.title_label, 1)

        self.time_left = QLabel()
        self.time_left.setObjectName("timeLeft")
        row.addWidget(self.time_left)
        self.update_time_left(task)

        self.complete_button = QPushButton("Complete")
        self.complete_button.setEnabled(not task.get("done", False))
        self.complete_button.clicked.connect(
            lambda _checked=False: self.complete_requested.emit(self.task_id)
        )
        row.addWidget(self.complete_button)

        remove_button = QPushButton("Remove")
        remove_button.setObjectName("secondaryButton")
        remove_button.clicked.connect(
            lambda _checked=False: self.remove_requested.emit(self.task_id)
        )
        row.addWidget(remove_button)

    def update_time_left(self, task: dict) -> None:
        text, overdue = time_left_text(task)
        self.time_left.setText(text)
        if self.time_left.property("overdue") != overdue:
            # Re-polish so the [overdue="true"] style rule is re-evaluated.
            self.time_left.setProperty("overdue", overdue)
            self.time_left.style().unpolish(self.time_left)
            self.time_left.style().polish(self.time_left)


class PetWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Wilson")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(MIN_WIDTH)
        # True while the code (not the user) is resizing the window.
        self._fitting = False
        # Saving the size is debounced so dragging the grip doesn't hammer the disk.
        self.size_save_timer = QTimer(self)
        self.size_save_timer.setSingleShot(True)
        self.size_save_timer.setInterval(400)
        self.size_save_timer.timeout.connect(self.save_state)

        app_data = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        self.state_path = Path(app_data) / "state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self.load_state()
        self.roll_over_day_if_needed()
        self.update_mood()

        self.card = QFrame(self)
        self.card.setObjectName("card")
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(15, 12, 15, 14)
        layout.setSpacing(9)

        title_bar = DragBar(self)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)
        self.name_heading = QLabel()
        self.name_heading.setStyleSheet("font-size: 16px; font-weight: 700;")
        self.theme_button = QPushButton()
        self.theme_button.setObjectName("secondaryButton")
        self.theme_button.setFixedWidth(30)
        self.theme_button.clicked.connect(self.toggle_theme)
        self.minimize_button = QPushButton()
        self.minimize_button.setObjectName("secondaryButton")
        self.minimize_button.setFixedWidth(30)
        self.minimize_button.clicked.connect(self.toggle_collapsed)
        close = QPushButton("×")
        close.setFixedWidth(30)
        close.setToolTip("Close")
        close.clicked.connect(self.close)
        title_layout.addWidget(self.name_heading)
        title_layout.addStretch()
        title_layout.addWidget(self.theme_button)
        title_layout.addWidget(self.minimize_button)
        title_layout.addWidget(close)
        layout.addWidget(title_bar)

        # Everything below the title bar lives in the body so it can be collapsed.
        self.body = QWidget()
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(9)
        layout.addWidget(self.body, 1)

        pet_row = QHBoxLayout()
        self.pet = QLabel()
        self.pet.setObjectName("pet")
        self.pet.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pet_row.addWidget(self.pet)
        self.mood_message = QLabel()
        self.mood_message.setObjectName("status")
        self.mood_message.setWordWrap(True)
        pet_row.addWidget(self.mood_message, 1)
        body_layout.addLayout(pet_row)

        mood_header = QHBoxLayout()
        mood_header.addWidget(QLabel("Mood"))
        mood_header.addStretch()
        self.mood_value = QLabel()
        mood_header.addWidget(self.mood_value)
        body_layout.addLayout(mood_header)
        self.mood_bar = QProgressBar()
        self.mood_bar.setRange(0, 100)
        self.mood_bar.setTextVisible(False)
        body_layout.addWidget(self.mood_bar)

        # The area below the mood bar switches between the task list and settings.
        self.pages = QStackedWidget()
        self.pages.addWidget(self.build_tasks_page())
        self.pages.addWidget(self.build_settings_page())
        body_layout.addWidget(self.pages, 1)

        self.feedback = QLabel("")
        self.feedback.setObjectName("status")
        body_layout.addWidget(self.feedback)
        self.confirm_dialog = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.card)

        # Drag the bottom-right corner to resize the widget.
        self.size_grip = QSizeGrip(self)
        self.size_grip.setToolTip("Drag to resize")

        self.apply_theme()
        self.apply_collapsed()
        self.fit_window_to_state()
        self.apply_startup_setting()
        self.render_tasks()
        self.refresh_view()
        self.save_state()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30_000)

    def build_tasks_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(9)

        page_layout.addWidget(self.section_label("Today's tasks"))
        add_row = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("What do you want to do?")
        self.task_input.returnPressed.connect(self.add_task)
        add_row.addWidget(self.task_input, 1)
        self.duration_input = QSpinBox()
        self.duration_input.setRange(5, 24 * 60)
        self.duration_input.setSingleStep(5)
        self.duration_input.setValue(DEFAULT_TASK_MINUTES)
        self.duration_input.setSuffix(" min")
        self.duration_input.setToolTip("How long you have to finish this task")
        add_row.addWidget(self.duration_input)
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_task)
        add_row.addWidget(add_button)
        page_layout.addLayout(add_row)

        self.task_list = QWidget()
        self.task_list_layout = QVBoxLayout(self.task_list)
        self.task_list_layout.setContentsMargins(0, 0, 0, 0)
        self.task_list_layout.setSpacing(6)
        self.task_rows: dict[str, TaskRow] = {}
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        # The list grows and shrinks with the window instead of a fixed height.
        self.scroll.setMinimumHeight(90)
        self.scroll.setWidget(self.task_list)
        page_layout.addWidget(self.scroll, 1)

        settings_button = QPushButton("⚙  Settings")
        settings_button.setObjectName("secondaryButton")
        settings_button.clicked.connect(lambda _checked=False: self.show_page(SETTINGS_PAGE))
        page_layout.addWidget(settings_button)
        return page

    def build_settings_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(6)

        header = QHBoxLayout()
        header.addWidget(self.section_label("Settings"))
        header.addStretch()
        back_button = QPushButton("Back")
        back_button.setObjectName("secondaryButton")
        back_button.clicked.connect(lambda _checked=False: self.show_page(TASKS_PAGE))
        header.addWidget(back_button)
        page_layout.addLayout(header)

        page_layout.addWidget(self.field_label("Dog's name"))
        self.name_input = QLineEdit(self.state["name"])
        self.name_input.setPlaceholderText("Dog's name")
        self.name_input.setMaxLength(24)
        self.name_input.editingFinished.connect(self.save_name)
        page_layout.addWidget(self.name_input)

        page_layout.addWidget(self.field_label("Dog's temperament"))
        self.temperament = QComboBox()
        self.temperament.addItems(list(TEMPERAMENT_MESSAGES))
        self.temperament.setCurrentText(self.state["temperament"])
        self.temperament.currentTextChanged.connect(self.save_temperament)
        page_layout.addWidget(self.temperament)

        page_layout.addWidget(self.field_label("Dog's icon"))
        self.dog_style = QComboBox()
        self.dog_style.addItem("\U0001F436  Classic dog", "\U0001F436")
        self.dog_style.addItem("\U0001F415  Dog", "\U0001F415")
        self.dog_style.addItem("\U0001F429  Poodle", "\U0001F429")
        self.dog_style.addItem("\U0001F9AE  Guide dog", "\U0001F9AE")
        style_index = self.dog_style.findData(self.state["dog_style"])
        self.dog_style.setCurrentIndex(max(style_index, 0))
        self.dog_style.currentIndexChanged.connect(self.save_dog_style)
        page_layout.addWidget(self.dog_style)

        self.startup_toggle = QCheckBox("Start Wilson when I sign into Windows")
        self.startup_toggle.setVisible(self.is_packaged_windows())
        self.startup_toggle.setChecked(bool(self.state.get("start_with_windows", True)))
        self.startup_toggle.toggled.connect(self.save_startup_setting)
        page_layout.addSpacing(4)
        page_layout.addWidget(self.startup_toggle)

        page_layout.addStretch(1)
        return page

    def show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)

    @staticmethod
    def section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-weight: 700; margin-top: 3px;")
        return label

    @staticmethod
    def field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("status")
        return label

    @staticmethod
    def default_state() -> dict:
        return {
            "name": "Wilson",
            "temperament": "Kind",
            "dog_style": "\U0001F436",
            "tasks": [],
            "day": date.today().isoformat(),
            "mood": 100.0,
            "mood_updated_at": datetime.now().isoformat(),
            "mood_frozen": False,
            "theme": "light",
            "collapsed": False,
            "size": [DEFAULT_WIDTH, DEFAULT_HEIGHT],
            "start_with_windows": bool(
                sys.platform == "win32" and getattr(sys, "frozen", False)
            ),
        }

    def load_state(self) -> dict:
        state = self.default_state()
        try:
            saved = json.loads(self.state_path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                state.update(saved)
        except (OSError, json.JSONDecodeError, TypeError):
            pass

        if state.get("temperament") not in TEMPERAMENT_MESSAGES:
            state["temperament"] = "Kind"
        if not isinstance(state.get("name"), str) or not state["name"].strip():
            state["name"] = "Wilson"
        if state.get("dog_style") not in {
            "\U0001F436", "\U0001F415", "\U0001F429", "\U0001F9AE"
        }:
            state["dog_style"] = "\U0001F436"
        if state.get("theme") not in THEMES:
            state["theme"] = "light"
        state["collapsed"] = bool(state.get("collapsed", False))
        size = state.get("size")
        if not (
            isinstance(size, list) and len(size) == 2
            and all(isinstance(value, int) and value > 0 for value in size)
        ):
            state["size"] = [DEFAULT_WIDTH, DEFAULT_HEIGHT]
        if not isinstance(state.get("tasks"), list):
            state["tasks"] = []
        state["tasks"] = [
            task for task in state["tasks"]
            if isinstance(task, dict) and task.get("title")
        ]
        for task in state["tasks"]:
            task.setdefault("id", str(uuid.uuid4()))
            task.setdefault("done", False)
            self.migrate_task_timing(task)
        try:
            state["mood"] = max(0.0, min(100.0, float(state["mood"])))
        except (TypeError, ValueError):
            state["mood"] = 100.0
        return state

    @staticmethod
    def migrate_task_timing(task: dict) -> None:
        """Give every task a duration and a due time, converting old clock deadlines."""
        try:
            task["duration_minutes"] = max(1, int(task["duration_minutes"]))
        except (KeyError, TypeError, ValueError):
            task["duration_minutes"] = DEFAULT_TASK_MINUTES
        try:
            datetime.fromisoformat(task["due_at"])
            return
        except (KeyError, TypeError, ValueError):
            pass
        due = None
        old_deadline = task.pop("deadline", None)
        if isinstance(old_deadline, str):
            try:
                clock = datetime.strptime(old_deadline, "%H:%M").time()
                due = datetime.combine(date.today(), clock)
            except ValueError:
                pass
        if due is None:
            due = datetime.now() + timedelta(minutes=task["duration_minutes"])
        task["due_at"] = due.isoformat(timespec="seconds")

    def save_state(self) -> None:
        try:
            self.state_path.write_text(
                json.dumps(self.state, indent=2), encoding="utf-8"
            )
        except OSError:
            feedback = getattr(self, "feedback", None)
            if feedback is not None:
                feedback.setText("Couldn't save your settings on this computer.")

    def roll_over_day_if_needed(self) -> None:
        today = date.today().isoformat()
        if self.state.get("day") == today:
            return
        self.state["day"] = today
        now = datetime.now()
        for task in self.state["tasks"]:
            task["done"] = False
            # Each new day restarts the task's countdown.
            task["due_at"] = (
                now + timedelta(minutes=task["duration_minutes"])
            ).isoformat(timespec="seconds")
        self.state["mood"] = 100.0
        self.state["mood_frozen"] = False
        self.state["mood_updated_at"] = now.isoformat()
        self.save_state()
        if hasattr(self, "task_rows"):
            self.render_tasks()

    def update_mood(self) -> None:
        if self.state.get("mood_frozen"):
            return
        now = datetime.now()
        try:
            previous = datetime.fromisoformat(self.state["mood_updated_at"])
        except (KeyError, TypeError, ValueError):
            previous = now
        elapsed_hours = max(0.0, (now - previous).total_seconds() / 3600)
        self.state["mood"] = max(
            0.0,
            float(self.state["mood"]) - elapsed_hours * MOOD_DECAY_PER_HOUR,
        )
        self.state["mood_updated_at"] = now.isoformat()

    def tick(self) -> None:
        self.roll_over_day_if_needed()
        self.update_mood()
        self.refresh_view()
        self.update_time_left_labels()
        self.save_state()

    def refresh_view(self) -> None:
        name = self.state["name"].strip() or "Your dog"
        self.name_heading.setText(name)
        self.setWindowTitle(name)

        mood = round(float(self.state["mood"]))
        self.mood_value.setText(f"{mood}%")
        self.mood_bar.setValue(mood)

        tasks = self.state["tasks"]
        complete_count = sum(task.get("done", False) for task in tasks)
        if tasks and complete_count == len(tasks):
            message_key = "done"
        elif complete_count:
            message_key = "progress"
        else:
            message_key = "idle"
        temperament = self.state["temperament"]
        self.mood_message.setText(TEMPERAMENT_MESSAGES[temperament][message_key])
        self.pet.setText(self.state["dog_style"])

    def render_tasks(self) -> None:
        while self.task_list_layout.count():
            item = self.task_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.task_rows = {}

        tasks = self.state["tasks"]
        if not tasks:
            empty = QLabel("Add a task to start today's list.")
            empty.setObjectName("status")
            self.task_list_layout.addWidget(empty)
        for task in tasks:
            row = TaskRow(task, self.task_list)
            row.complete_requested.connect(self.confirm_task)
            row.remove_requested.connect(self.remove_task)
            self.task_list_layout.addWidget(row)
            self.task_rows[task["id"]] = row
        self.task_list_layout.addStretch(1)

    def update_time_left_labels(self) -> None:
        for task in self.state["tasks"]:
            row = self.task_rows.get(task["id"])
            if row is not None:
                row.update_time_left(task)

    def add_task(self) -> None:
        title = self.task_input.text().strip()
        if not title:
            self.task_input.setFocus()
            return

        self.update_mood()
        duration = self.duration_input.value()
        due = datetime.now() + timedelta(minutes=duration)
        self.state["tasks"].append({
            "id": str(uuid.uuid4()),
            "title": title,
            "duration_minutes": duration,
            "due_at": due.isoformat(timespec="seconds"),
            "done": False,
        })
        self.state["mood_frozen"] = False
        self.state["mood_updated_at"] = datetime.now().isoformat()
        self.task_input.clear()
        self.feedback.clear()
        self.render_tasks()
        self.refresh_view()
        self.save_state()

    def confirm_task(self, task_id: str) -> None:
        task = next((item for item in self.state["tasks"] if item["id"] == task_id), None)
        if not task or task.get("done"):
            return

        if self.confirm_dialog is not None:
            self.confirm_dialog.raise_()
            self.confirm_dialog.activateWindow()
            return

        dialog = QMessageBox(self)
        dialog.setWindowTitle("Confirm task")
        dialog.setText(f"Have you completed this task?\n\n{task['title']}")
        dialog.setStyleSheet(self.styleSheet())
        dialog.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        dialog.buttonClicked.connect(
            lambda button, active=dialog, active_task_id=task_id:
                self.handle_task_confirmation(active, active_task_id, button)
        )
        self.show_task_dialog(dialog)

    def show_task_dialog(self, dialog: QMessageBox) -> None:
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setWindowFlags(
            dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.confirm_dialog = dialog
        dialog.finished.connect(
            lambda _result, active=dialog: self.clear_confirm_dialog(active)
        )
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def show_not_yet_message(self) -> None:
        if self.confirm_dialog is not None:
            return
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Not yet")
        dialog.setText("Come back when you finish the task.")
        dialog.setStyleSheet(self.styleSheet())
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.setDefaultButton(QMessageBox.StandardButton.Ok)
        self.show_task_dialog(dialog)

    def handle_task_confirmation(self, dialog, task_id: str, button) -> None:
        answer = dialog.standardButton(button)
        if answer == QMessageBox.StandardButton.No:
            self.confirm_dialog = None
            dialog.close()
            QTimer.singleShot(0, self.show_not_yet_message)
            return
        if answer == QMessageBox.StandardButton.Yes:
            dialog.close()
            self.mark_task_complete(task_id)
        elif answer == QMessageBox.StandardButton.Ok:
            dialog.close()

    def clear_confirm_dialog(self, dialog) -> None:
        if self.confirm_dialog is dialog:
            self.confirm_dialog = None

    def mark_task_complete(self, task_id: str) -> None:
        task = next((item for item in self.state["tasks"] if item["id"] == task_id), None)
        if not task or task.get("done"):
            return

        self.update_mood()
        task["done"] = True
        reward = max(5.0, 60.0 / max(1, len(self.state["tasks"])))
        self.state["mood"] = min(100.0, float(self.state["mood"]) + reward)
        if self.state["tasks"] and all(item.get("done") for item in self.state["tasks"]):
            self.state["mood"] = 100.0
            self.state["mood_frozen"] = True

        self.feedback.setText("Good job!")
        self.render_tasks()
        self.refresh_view()
        self.save_state()
        QTimer.singleShot(3000, self.feedback.clear)

    def remove_task(self, task_id: str) -> None:
        self.update_mood()
        self.state["tasks"] = [
            task for task in self.state["tasks"] if task["id"] != task_id
        ]
        if self.state["tasks"] and all(task.get("done") for task in self.state["tasks"]):
            self.state["mood"] = 100.0
            self.state["mood_frozen"] = True
        self.render_tasks()
        self.refresh_view()
        self.save_state()

    def save_name(self) -> None:
        self.state["name"] = self.name_input.text().strip() or "Wilson"
        self.name_input.setText(self.state["name"])
        self.refresh_view()
        self.save_state()

    def save_temperament(self, temperament: str) -> None:
        self.state["temperament"] = temperament
        self.refresh_view()
        self.save_state()

    def save_dog_style(self) -> None:
        self.state["dog_style"] = self.dog_style.currentData()
        self.refresh_view()
        self.save_state()

    def toggle_theme(self) -> None:
        self.state["theme"] = "dark" if self.state["theme"] == "light" else "light"
        self.apply_theme()
        self.save_state()

    def apply_theme(self) -> None:
        self.setStyleSheet(build_stylesheet(THEMES[self.state["theme"]]))
        if self.state["theme"] == "light":
            self.theme_button.setText("☾")
            self.theme_button.setToolTip("Switch to dark mode")
        else:
            self.theme_button.setText("☀")
            self.theme_button.setToolTip("Switch to light mode")
        if self.confirm_dialog is not None:
            self.confirm_dialog.setStyleSheet(self.styleSheet())

    def toggle_collapsed(self) -> None:
        self.state["collapsed"] = not self.state["collapsed"]
        self.apply_collapsed()
        self.save_state()

    def apply_collapsed(self) -> None:
        collapsed = self.state["collapsed"]
        # Ignore the layout's own resizes while switching, so the saved size survives.
        self._fitting = True
        self.body.setVisible(not collapsed)
        self.minimize_button.setText("+" if collapsed else "–")
        self.minimize_button.setToolTip("Expand" if collapsed else "Minimize")
        if hasattr(self, "size_grip"):
            self.size_grip.setVisible(not collapsed)
        # Let the layout settle, then shrink to the title bar or restore the saved size.
        QTimer.singleShot(0, self.fit_window_to_state)

    def fit_window_to_state(self) -> None:
        self._fitting = True
        self.layout().activate()
        width, height = self.state["size"]
        width = max(width, MIN_WIDTH)
        if self.state["collapsed"]:
            height = self.minimumSizeHint().height()
        else:
            height = max(height, self.minimumSizeHint().height())
        self.resize(width, height)
        self._fitting = False

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        grip = getattr(self, "size_grip", None)
        if grip is None:
            return
        grip.move(self.width() - grip.width() - 6, self.height() - grip.height() - 6)
        grip.raise_()
        # Only remember sizes the user chose while the widget is expanded.
        if not self._fitting and not self.state["collapsed"]:
            self.state["size"] = [self.width(), self.height()]
            self.size_save_timer.start()

    @staticmethod
    def is_packaged_windows() -> bool:
        return sys.platform == "win32" and bool(getattr(sys, "frozen", False))

    def save_startup_setting(self, enabled: bool) -> None:
        self.state["start_with_windows"] = enabled
        self.save_state()
        self.apply_startup_setting()

    def apply_startup_setting(self) -> None:
        # Development runs never modify Windows startup settings.
        if not self.is_packaged_windows():
            return
        try:
            import winreg

            run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE
            ) as key:
                if self.state.get("start_with_windows", True):
                    winreg.SetValueEx(
                        key,
                        "WilsonDogSelfHelp",
                        0,
                        winreg.REG_SZ,
                        f'"{sys.executable}"',
                    )
                else:
                    try:
                        winreg.DeleteValue(key, "WilsonDogSelfHelp")
                    except FileNotFoundError:
                        pass
        except OSError:
            self.feedback.setText(
                "Windows couldn't update the sign-in startup setting."
            )

    def closeEvent(self, event) -> None:
        self.update_mood()
        self.save_state()
        super().closeEvent(event)
        if event.isAccepted():
            QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Tool windows should remain open when a child dialog closes.
    app.setQuitOnLastWindowClosed(False)
    app.setOrganizationName("WilsonDogSelfHelp")
    app.setApplicationName("Wilson")

    instance_mutex = acquire_instance_mutex()
    if instance_mutex is None:
        notice = QMessageBox()
        notice.setWindowTitle("Wilson is already running")
        notice.setText("Only one copy of Wilson can run at a time.")
        notice.setStyleSheet("""
            QMessageBox { background: #fffaf0; color: #332d27; }
            QMessageBox QLabel { background: transparent; color: #332d27; }
            QMessageBox QPushButton { background: #e9a86c; color: #30251c;
                                     min-width: 78px; padding: 7px 10px; }
        """)
        notice.exec()
        sys.exit(0)

    widget = PetWidget()
    widget.move(80, 100)
    widget.show()
    sys.exit(app.exec())
