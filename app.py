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

from PySide6.QtCore import QDate, QDateTime, QStandardPaths, QTime, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QTextCharFormat
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCalendarWidget,
    QComboBox,
    QCheckBox,
    QDateTimeEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


MOOD_DECAY_PER_HOUR = 2.0
ERROR_ALREADY_EXISTS = 183
DEFAULT_TASK_MINUTES = 60
MIN_WIDTH = 340
DEFAULT_WIDTH = 390
DEFAULT_HEIGHT = 620
TASKS_PAGE = 0
SETTINGS_PAGE = 1
CALENDAR_PAGE = 2
DEFAULT_END_TIME = "23:55"

# How a task's deadline is set. Countdown and "end by" tasks repeat every day;
# dated tasks happen once and can be days away.
KIND_COUNTDOWN = "countdown"
KIND_TIME = "time"
KIND_DATE = "date"
KIND_WEEKLY = "weekly"
TASK_KINDS = (KIND_COUNTDOWN, KIND_TIME, KIND_DATE, KIND_WEEKLY)
# Kinds whose due time is a fixed moment, so they can sit under "Upcoming".
SCHEDULED_KINDS = (KIND_DATE, KIND_WEEKLY)
WEEKDAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


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
        QLineEdit, QComboBox, QAbstractSpinBox {{
            background: {p['input']}; border: 1px solid {p['input_border']};
            border-radius: 7px; padding: 6px; color: {p['text']};
        }}
        QLabel#sectionNote {{ color: {p['faint']}; font-size: 11px; font-weight: 700;
                             margin-top: 4px; }}
        QPushButton#segment {{ background: {p['secondary']}; color: {p['secondary_text']};
                              padding: 6px 8px; }}
        QPushButton#segment:hover:!checked {{ background: {p['border']}; }}
        QPushButton#segment:checked {{ background: {p['accent']}; color: {p['accent_text']};
                                      font-weight: 700; }}
        QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {p['card']}; }}
        QCalendarWidget QToolButton {{ color: {p['text']}; background: transparent;
                                      border: 0; padding: 4px 6px; font-weight: 700; }}
        QCalendarWidget QToolButton:hover {{ background: {p['secondary']};
                                            border-radius: 6px; }}
        QCalendarWidget QToolButton::menu-indicator {{ image: none; }}
        QCalendarWidget QMenu {{ background: {p['input']}; color: {p['text']}; }}
        QCalendarWidget QSpinBox {{ padding: 2px; }}
        QCalendarWidget QAbstractItemView {{
            background: {p['input']}; color: {p['text']}; outline: 0;
            selection-background-color: {p['text']}; selection-color: {p['card']};
        }}
        QCalendarWidget QAbstractItemView:disabled {{ color: {p['disabled_text']}; }}
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
        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px 0 2px 2px; }}
        QScrollBar::handle:vertical {{ background: {p['input_border']}; border-radius: 3px;
                                      min-height: 24px; }}
        QScrollBar::handle:vertical:hover {{ background: {p['popup_border']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    """


def clock_text(moment: datetime) -> str:
    """Format a time as e.g. '11:55 PM' (Windows strftime has no %-I)."""
    return moment.strftime("%I:%M %p").lstrip("0")


def next_occurrence(end_time: str, now: datetime | None = None) -> datetime:
    """The next time the clock reads end_time ('HH:MM'): today, or tomorrow if it has passed."""
    now = now or datetime.now()
    due = datetime.combine(now.date(), datetime.strptime(end_time, "%H:%M").time())
    if due <= now:
        due += timedelta(days=1)
    return due


def next_weekly_due(
    weekdays: list[int], end_time: str, now: datetime | None = None,
    allow_passed_today: bool = False,
) -> datetime:
    """The next selected weekday at end_time. Today counts if the time hasn't
    passed yet, or always when allow_passed_today (used by the daily reset)."""
    now = now or datetime.now()
    clock = datetime.strptime(end_time, "%H:%M").time()
    for offset in range(8):
        day = now.date() + timedelta(days=offset)
        if day.weekday() not in weekdays:
            continue
        due = datetime.combine(day, clock)
        if offset == 0 and due <= now and not allow_passed_today:
            continue
        return due
    raise ValueError("A weekly task needs at least one weekday.")


def weekdays_text(weekdays: list[int]) -> str:
    days = sorted(set(weekdays))
    if days == list(range(7)):
        return "Every day"
    if days == list(range(5)):
        return "Weekdays"
    if days == [5, 6]:
        return "Weekends"
    return ", ".join(WEEKDAY_NAMES[day] for day in days)


def task_due(task: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(task["due_at"])
    except (KeyError, TypeError, ValueError):
        return None


def time_left_text(task: dict) -> tuple[str, bool]:
    """Return a short label describing when a task is due, and whether it is overdue."""
    if task.get("done"):
        return "Done", False
    due = task_due(task)
    if due is None:
        return "", False

    kind = task.get("kind", KIND_COUNTDOWN)
    today = date.today()
    if kind == KIND_TIME:
        when = f"By {clock_text(due)}"
        if due.date() > today:
            when += " tomorrow"
    elif kind == KIND_DATE:
        if due.date() == today:
            day = "today"
        elif due.date() == today + timedelta(days=1):
            day = "tomorrow"
        else:
            day = due.strftime("%a %d %b").replace(" 0", " ")
        when = f"Due {day}, {clock_text(due)}"
    elif kind == KIND_WEEKLY:
        when = weekdays_text(task.get("weekdays", []))
        if due.date() <= today:
            when += f" · by {clock_text(due)}"
        elif due.date() == today + timedelta(days=1):
            when += f" · tomorrow by {clock_text(due)}"
        else:
            when += f" · next {due.strftime('%a')} by {clock_text(due)}"
    else:
        when = f"{task.get('duration_minutes', DEFAULT_TASK_MINUTES)} min countdown"

    seconds = (due - datetime.now()).total_seconds()
    if seconds <= 0:
        return f"{when} · Overdue", True
    total_minutes = math.ceil(seconds / 60)
    days, remainder = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remainder, 60)
    if days:
        left = f"{days}d {hours}h left"
    elif hours:
        left = f"{hours}h {minutes:02d}m left"
    else:
        left = f"{minutes}m left"
    return f"{when} · {left}", False


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

    def __init__(
        self, task: dict, parent: QWidget | None = None, can_complete: bool = True
    ) -> None:
        super().__init__(parent)
        self.task_id = task["id"]
        self.setObjectName("taskRow")
        # Keep each row at its natural height so a long list scrolls instead of
        # squashing; resizeEvent grows it to fit wrapped text.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 7, 8, 7)
        row.setSpacing(8)

        # Title on top, with the due/countdown details underneath it.
        text_column = QVBoxLayout()
        text_column.setSpacing(1)
        title = html.escape(task["title"])
        if task.get("done", False):
            title = f"<s>{title}</s>"
        self.title_label = QLabel(title)
        self.title_label.setWordWrap(True)
        self.title_label.setTextFormat(Qt.TextFormat.RichText)
        text_column.addWidget(self.title_label)

        self.time_left = QLabel()
        self.time_left.setObjectName("timeLeft")
        self.time_left.setWordWrap(True)
        text_column.addWidget(self.time_left)
        row.addLayout(text_column, 1)
        self.update_time_left(task)

        self.complete_button = QPushButton("Complete")
        self.complete_button.setEnabled(can_complete and not task.get("done", False))
        if not can_complete:
            self.complete_button.setToolTip("You can complete this on its next scheduled day.")
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

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fit_height()

    def fit_height(self) -> None:
        """Make the row tall enough for its wrapped title and details at this width."""
        needed = self.layout().heightForWidth(self.width())
        if needed > 0 and needed != self.minimumHeight():
            self.setMinimumHeight(needed)

    def update_time_left(self, task: dict) -> None:
        text, overdue = time_left_text(task)
        self.time_left.setText(text)
        if self.isVisible():
            self.fit_height()
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
        self.pages.addWidget(self.build_calendar_page())
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
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("What do you want to do?")
        self.task_input.returnPressed.connect(self.add_task)
        page_layout.addWidget(self.task_input)

        # Pick how the deadline is set: a countdown, a time of day, or a date.
        kind_row = QHBoxLayout()
        kind_row.setSpacing(6)
        self.kind_buttons = QButtonGroup(self)
        self.kind_buttons.setExclusive(True)
        kind_options = (
            (KIND_COUNTDOWN, "Countdown", "Finish within a set number of minutes. Repeats daily."),
            (KIND_TIME, "End by", "Finish by a time of day, e.g. 11:55 PM. Repeats daily."),
            (KIND_DATE, "Date", "A one-off task due on a date, even days away."),
            (KIND_WEEKLY, "Weekly", "Repeats on the weekdays you pick, finishing by a set time."),
        )
        for index, (_kind, label, tip) in enumerate(kind_options):
            button = QPushButton(label)
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setToolTip(tip)
            self.kind_buttons.addButton(button, index)
            kind_row.addWidget(button, 1)
        self.kind_buttons.idToggled.connect(self.on_kind_toggled)
        page_layout.addLayout(kind_row)

        # Weekday toggles, only shown for weekly tasks.
        self.weekday_row = QWidget()
        weekday_layout = QHBoxLayout(self.weekday_row)
        weekday_layout.setContentsMargins(0, 0, 0, 0)
        weekday_layout.setSpacing(4)
        self.weekday_buttons: list[QPushButton] = []
        for index, name in enumerate(WEEKDAY_NAMES):
            button = QPushButton(name[:2])
            button.setObjectName("segment")
            button.setCheckable(True)
            button.setToolTip(name)
            button.setMinimumWidth(0)
            weekday_layout.addWidget(button, 1)
            self.weekday_buttons.append(button)
        self.weekday_row.setVisible(False)
        page_layout.addWidget(self.weekday_row)

        add_row = QHBoxLayout()
        self.deadline_inputs = QStackedWidget()

        self.duration_input = QSpinBox()
        self.duration_input.setRange(5, 24 * 60)
        self.duration_input.setSingleStep(5)
        self.duration_input.setValue(DEFAULT_TASK_MINUTES)
        self.duration_input.setSuffix(" min")
        self.duration_input.setToolTip("How long you have to finish this task")
        self.deadline_inputs.addWidget(self.duration_input)

        self.end_time_input = QTimeEdit(QTime.fromString(DEFAULT_END_TIME, "HH:mm"))
        self.end_time_input.setDisplayFormat("h:mm AP")
        self.end_time_input.setToolTip("Finish by this time (tomorrow if it has already passed)")
        self.deadline_inputs.addWidget(self.end_time_input)

        self.due_date_input = QDateTimeEdit()
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDisplayFormat("ddd d MMM, h:mm AP")
        self.due_date_input.setToolTip("Pick the day and time this task is due")
        self.reset_due_date_input()
        self.deadline_inputs.addWidget(self.due_date_input)

        add_row.addWidget(self.deadline_inputs, 1)
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_task)
        add_row.addWidget(add_button)
        page_layout.addLayout(add_row)
        self.kind_buttons.button(0).setChecked(True)

        self.task_list = QWidget()
        self.task_list_layout = QVBoxLayout(self.task_list)
        self.task_list_layout.setContentsMargins(0, 0, 0, 0)
        self.task_list_layout.setSpacing(6)
        self.task_rows: dict[str, TaskRow] = {}
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # The list grows and shrinks with the window instead of a fixed height.
        self.scroll.setMinimumHeight(90)
        self.scroll.setWidget(self.task_list)
        page_layout.addWidget(self.scroll, 1)

        nav_row = QHBoxLayout()
        calendar_button = QPushButton("\U0001F4C5  Calendar")
        calendar_button.setObjectName("secondaryButton")
        calendar_button.clicked.connect(lambda _checked=False: self.show_page(CALENDAR_PAGE))
        nav_row.addWidget(calendar_button, 1)
        settings_button = QPushButton("⚙  Settings")
        settings_button.setObjectName("secondaryButton")
        settings_button.clicked.connect(lambda _checked=False: self.show_page(SETTINGS_PAGE))
        nav_row.addWidget(settings_button, 1)
        page_layout.addLayout(nav_row)
        return page

    def build_calendar_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(6)

        header = QHBoxLayout()
        header.addWidget(self.section_label("Calendar"))
        header.addStretch()
        back_button = QPushButton("Back")
        back_button.setObjectName("secondaryButton")
        back_button.clicked.connect(lambda _checked=False: self.show_page(TASKS_PAGE))
        header.addWidget(back_button)
        page_layout.addLayout(header)

        # Days with a dated task due are highlighted; pick one to see its tasks.
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.calendar.setHorizontalHeaderFormat(
            QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
        )
        self.calendar.setMinimumHeight(190)
        self.calendar.selectionChanged.connect(self.on_calendar_selection)
        page_layout.addWidget(self.calendar)

        self.calendar_day_label = QLabel()
        self.calendar_day_label.setStyleSheet("font-weight: 700;")
        page_layout.addWidget(self.calendar_day_label)

        self.calendar_day_list = QWidget()
        self.calendar_day_layout = QVBoxLayout(self.calendar_day_list)
        self.calendar_day_layout.setContentsMargins(0, 0, 0, 0)
        self.calendar_day_layout.setSpacing(6)
        self.calendar_rows: dict[str, TaskRow] = {}
        day_scroll = QScrollArea()
        day_scroll.setWidgetResizable(True)
        day_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        day_scroll.setMinimumHeight(60)
        day_scroll.setWidget(self.calendar_day_list)
        page_layout.addWidget(day_scroll, 1)

        self.add_on_day_button = QPushButton("Add a task on this day")
        self.add_on_day_button.clicked.connect(self.start_task_on_selected_day)
        page_layout.addWidget(self.add_on_day_button)
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

        self.startup_toggle = QCheckBox("Auto-start with Windows")
        self.startup_toggle.setVisible(self.is_packaged_windows())
        self.startup_toggle.setChecked(bool(self.state.get("start_with_windows", True)))
        self.startup_toggle.toggled.connect(self.save_startup_setting)
        page_layout.addSpacing(4)
        page_layout.addWidget(self.startup_toggle)

        page_layout.addStretch(1)
        return page

    def show_page(self, index: int) -> None:
        if index == CALENDAR_PAGE:
            self.render_calendar_day()
        self.pages.setCurrentIndex(index)

    def on_kind_toggled(self, index: int, checked: bool) -> None:
        if not checked:
            return
        kind = TASK_KINDS[index]
        # Weekly tasks reuse the "end by" time box, plus the weekday toggles.
        input_index = TASK_KINDS.index(KIND_TIME) if kind == KIND_WEEKLY else index
        self.deadline_inputs.setCurrentIndex(input_index)
        self.weekday_row.setVisible(kind == KIND_WEEKLY)

    def selected_weekdays(self) -> list[int]:
        return [day for day, button in enumerate(self.weekday_buttons) if button.isChecked()]

    def selected_kind(self) -> str:
        return TASK_KINDS[max(0, self.kind_buttons.checkedId())]

    def reset_due_date_input(self) -> None:
        """Default the date picker to tomorrow at 5 PM, and forbid past times."""
        now = QDateTime.currentDateTime()
        self.due_date_input.setMinimumDateTime(now)
        self.due_date_input.setDateTime(QDateTime(now.date().addDays(1), QTime(17, 0)))

    def start_task_on_selected_day(self) -> None:
        """Jump to the add form with 'Due date' picked and the calendar's day filled in."""
        selected = self.calendar.selectedDate()
        self.due_date_input.setMinimumDateTime(QDateTime.currentDateTime())
        time_of_day = self.due_date_input.time()
        self.due_date_input.setDateTime(QDateTime(selected, time_of_day))
        self.kind_buttons.button(TASK_KINDS.index(KIND_DATE)).setChecked(True)
        self.show_page(TASKS_PAGE)
        self.task_input.setFocus()

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
    def valid_clock(value) -> bool:
        try:
            datetime.strptime(value, "%H:%M")
            return True
        except (TypeError, ValueError):
            return False

    @classmethod
    def migrate_task_timing(cls, task: dict) -> None:
        """Give every task a kind and a due time, converting older saved formats."""
        old_deadline = task.pop("deadline", None)
        if task.get("kind") not in TASK_KINDS:
            # Very old versions stored "end by" times as a bare 'HH:MM' deadline.
            if cls.valid_clock(old_deadline):
                task["kind"] = KIND_TIME
                task["end_time"] = old_deadline
            else:
                task["kind"] = KIND_COUNTDOWN
        if task["kind"] in (KIND_TIME, KIND_WEEKLY) and not cls.valid_clock(task.get("end_time")):
            task["kind"] = KIND_COUNTDOWN
        if task["kind"] == KIND_WEEKLY:
            weekdays = task.get("weekdays")
            if isinstance(weekdays, list):
                weekdays = sorted({day for day in weekdays if isinstance(day, int) and 0 <= day <= 6})
            if not weekdays:
                task["kind"] = KIND_COUNTDOWN
            else:
                task["weekdays"] = weekdays
        try:
            task["duration_minutes"] = max(1, int(task["duration_minutes"]))
        except (KeyError, TypeError, ValueError):
            task["duration_minutes"] = DEFAULT_TASK_MINUTES

        if task_due(task) is not None:
            return
        if task["kind"] == KIND_TIME:
            clock = datetime.strptime(task["end_time"], "%H:%M").time()
            due = datetime.combine(date.today(), clock)
        elif task["kind"] == KIND_WEEKLY:
            due = next_weekly_due(task["weekdays"], task["end_time"], allow_passed_today=True)
        else:
            # A dated task without a date can't be recovered; treat it as a countdown.
            task["kind"] = KIND_COUNTDOWN
            due = datetime.now() + timedelta(minutes=task["duration_minutes"])
        task["due_at"] = due.isoformat(timespec="seconds")

    @staticmethod
    def is_today_task(task: dict) -> bool:
        """Daily tasks always count for today; dated and weekly tasks only on their day."""
        if task.get("kind") not in SCHEDULED_KINDS:
            return True
        due = task_due(task)
        return due is None or due.date() <= date.today()

    def today_tasks(self) -> list[dict]:
        return [task for task in self.state["tasks"] if self.is_today_task(task)]

    def dated_tasks(self) -> list[dict]:
        tasks = [task for task in self.state["tasks"] if task.get("kind") == KIND_DATE]
        return sorted(tasks, key=lambda task: task["due_at"])

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
        kept = []
        for task in self.state["tasks"]:
            if task["kind"] == KIND_DATE:
                # Dated tasks are one-offs: drop finished ones, keep the rest as they are.
                if not task.get("done"):
                    kept.append(task)
                continue
            task["done"] = False
            # Each new day restarts countdowns, moves "end by" times to today,
            # and moves weekly tasks to today (if it's one of their days) or their next day.
            if task["kind"] == KIND_WEEKLY:
                due = next_weekly_due(
                    task["weekdays"], task["end_time"], now, allow_passed_today=True
                )
            elif task["kind"] == KIND_TIME:
                clock = datetime.strptime(task["end_time"], "%H:%M").time()
                due = datetime.combine(now.date(), clock)
            else:
                due = now + timedelta(minutes=task["duration_minutes"])
            task["due_at"] = due.isoformat(timespec="seconds")
            kept.append(task)
        self.state["tasks"] = kept
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

        tasks = self.today_tasks()
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

    @staticmethod
    def clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                # Hide now so old rows never flash behind new ones before deletion.
                item.widget().hide()
                item.widget().deleteLater()

    def make_task_row(self, task: dict, parent: QWidget) -> TaskRow:
        # A weekly task can't be ticked off before its day; it would just reset.
        can_complete = task.get("kind") != KIND_WEEKLY or self.is_today_task(task)
        row = TaskRow(task, parent, can_complete)
        row.complete_requested.connect(self.confirm_task)
        row.remove_requested.connect(self.remove_task)
        return row

    @staticmethod
    def note_label(text: str, object_name: str = "status") -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        return label

    def render_tasks(self) -> None:
        self.clear_layout(self.task_list_layout)
        self.task_rows = {}

        today = self.today_tasks()
        upcoming = sorted(
            (task for task in self.state["tasks"] if not self.is_today_task(task)),
            key=lambda task: task["due_at"],
        )
        if not today:
            self.task_list_layout.addWidget(
                self.note_label("Add a task to start today's list.")
            )
        for task in today:
            row = self.make_task_row(task, self.task_list)
            self.task_list_layout.addWidget(row)
            self.task_rows[task["id"]] = row
        if upcoming:
            self.task_list_layout.addWidget(self.note_label("UPCOMING", "sectionNote"))
            for task in upcoming:
                row = self.make_task_row(task, self.task_list)
                self.task_list_layout.addWidget(row)
                self.task_rows[task["id"]] = row
        self.task_list_layout.addStretch(1)

        self.refresh_calendar_marks()
        self.render_calendar_day()

    def refresh_calendar_marks(self) -> None:
        """Highlight days with dated tasks: accent if any are unfinished, green if all done."""
        palette = THEMES[self.state["theme"]]
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())  # clears every mark
        days: dict[date, bool] = {}
        for task in self.dated_tasks():
            day = task_due(task).date()
            days[day] = days.get(day, False) or not task.get("done")
        for day, has_pending in days.items():
            mark = QTextCharFormat()
            mark.setFontWeight(700)
            mark.setBackground(QColor(palette["accent"] if has_pending else palette["good"]))
            mark.setForeground(QColor(palette["accent_text"]))
            self.calendar.setDateTextFormat(QDate(day.year, day.month, day.day), mark)
        # Paint the selected day ourselves (inverted colours) so it always shows,
        # even when the calendar's own selection highlight isn't drawn.
        selected = QTextCharFormat()
        selected.setFontWeight(700)
        selected.setBackground(QColor(palette["text"]))
        selected.setForeground(QColor(palette["card"]))
        self.calendar.setDateTextFormat(self.calendar.selectedDate(), selected)

    def on_calendar_selection(self) -> None:
        self.refresh_calendar_marks()
        self.render_calendar_day()

    def render_calendar_day(self) -> None:
        self.clear_layout(self.calendar_day_layout)
        self.calendar_rows = {}
        day = self.calendar.selectedDate().toPython()
        today = date.today()
        if day == today:
            title = "Due today"
        elif day == today + timedelta(days=1):
            title = "Due tomorrow"
        else:
            title = "Due " + day.strftime("%A %d %B").replace(" 0", " ")
        self.calendar_day_label.setText(title)

        tasks = [task for task in self.dated_tasks() if task_due(task).date() == day]
        weekly = [
            task for task in self.state["tasks"]
            if task.get("kind") == KIND_WEEKLY and day.weekday() in task["weekdays"]
        ]
        if not tasks and not weekly:
            self.calendar_day_layout.addWidget(
                self.note_label("Nothing scheduled this day. Countdown and "
                                "end-by tasks repeat daily on the main list.")
            )
        for task in tasks:
            row = self.make_task_row(task, self.calendar_day_list)
            self.calendar_day_layout.addWidget(row)
            self.calendar_rows[task["id"]] = row
        for task in weekly:
            if task_due(task).date() == day:
                # This is the task's current occurrence, so it can be completed here.
                row = self.make_task_row(task, self.calendar_day_list)
                self.calendar_day_layout.addWidget(row)
                self.calendar_rows[task["id"]] = row
            else:
                clock = clock_text(datetime.strptime(task["end_time"], "%H:%M"))
                self.calendar_day_layout.addWidget(self.note_label(
                    f"↻  {task['title']}: weekly, by {clock}"
                ))
        self.calendar_day_layout.addStretch(1)
        self.add_on_day_button.setEnabled(day >= today)

    def update_time_left_labels(self) -> None:
        for task in self.state["tasks"]:
            for rows in (self.task_rows, self.calendar_rows):
                row = rows.get(task["id"])
                if row is not None:
                    row.update_time_left(task)

    def add_task(self) -> None:
        title = self.task_input.text().strip()
        if not title:
            self.task_input.setFocus()
            return

        kind = self.selected_kind()
        now = datetime.now()
        task = {
            "id": str(uuid.uuid4()),
            "title": title,
            "kind": kind,
            "duration_minutes": self.duration_input.value(),
            "done": False,
        }
        if kind == KIND_TIME:
            task["end_time"] = self.end_time_input.time().toString("HH:mm")
            due = next_occurrence(task["end_time"], now)
        elif kind == KIND_DATE:
            due = self.due_date_input.dateTime().toPython().replace(second=0, microsecond=0)
            if due <= now:
                self.feedback.setText("Pick a due time that hasn't passed yet.")
                return
        elif kind == KIND_WEEKLY:
            weekdays = self.selected_weekdays()
            if not weekdays:
                self.feedback.setText("Pick at least one day for a weekly task.")
                return
            task["weekdays"] = weekdays
            task["end_time"] = self.end_time_input.time().toString("HH:mm")
            due = next_weekly_due(weekdays, task["end_time"], now)
        else:
            due = now + timedelta(minutes=task["duration_minutes"])
        task["due_at"] = due.isoformat(timespec="seconds")

        self.update_mood()
        self.state["tasks"].append(task)
        if self.is_today_task(task):
            # A new task for today means the list is no longer all done.
            self.state["mood_frozen"] = False
            self.state["mood_updated_at"] = now.isoformat()
            self.feedback.clear()
        else:
            day = due.strftime("%a %d %b").replace(" 0", " ")
            if kind == KIND_WEEKLY:
                self.feedback.setText(f"Weekly task added. Next one is {day}.")
            else:
                self.feedback.setText(f"Added to your calendar for {day}.")
            QTimer.singleShot(4000, self.feedback.clear)
        self.task_input.clear()
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
        today = self.today_tasks()
        reward = max(5.0, 60.0 / max(1, len(today)))
        self.state["mood"] = min(100.0, float(self.state["mood"]) + reward)
        if today and all(item.get("done") for item in today):
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
        today = self.today_tasks()
        if today and all(task.get("done") for task in today):
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
        # Calendars colour weekends and headers themselves, so match them to the theme.
        palette = THEMES[self.state["theme"]]
        day_format = QTextCharFormat()
        day_format.setForeground(QColor(palette["text"]))
        header_format = QTextCharFormat()
        header_format.setForeground(QColor(palette["faint"]))
        header_format.setFontWeight(700)
        header_format.setBackground(QColor(palette["input"]))
        for calendar in (self.calendar, self.due_date_input.calendarWidget()):
            for weekday in Qt.DayOfWeek:
                calendar.setWeekdayTextFormat(weekday, day_format)
            calendar.setHeaderTextFormat(header_format)
            # The built-in month arrows are icons that vanish on some themes; use text.
            for name, arrow in (("qt_calendar_prevmonth", "‹"), ("qt_calendar_nextmonth", "›")):
                button = calendar.findChild(QToolButton, name)
                if button is not None:
                    button.setIcon(QIcon())
                    button.setText(arrow)
                    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
                    button.setStyleSheet("font-size: 18px; padding: 0 10px;")
        self.refresh_calendar_marks()
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
