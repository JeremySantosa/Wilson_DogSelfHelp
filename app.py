#The app itself
from __future__ import annotations

import html
import json
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QTime, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)


MOOD_DECAY_PER_HOUR = 2.0

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
    "Asshole": {
        "idle": "tf you looking at me for",
        "progress": "ayyy you got it done, now do the rest",
        "done": "you not bad bro",
    },
}


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

        deadline = QLabel(f"by {task['deadline']}")
        deadline.setObjectName("deadline")
        row.addWidget(deadline)

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
        self.setFixedWidth(390)

        app_data = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        self.state_path = Path(app_data) / "state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self.load_state()
        self.roll_over_day_if_needed()
        self.update_mood()

        self.setStyleSheet("""
            QFrame#card { background: #fffaf0; border: 1px solid #eadfca;
                          border-radius: 18px; }
            QLabel { color: #332d27; }
            QLabel#pet { font-size: 52px; }
            QLabel#status { color: #66594c; }
            QLabel#deadline { color: #76695d; font-size: 11px; }
            QLineEdit, QComboBox, QTimeEdit {
                background: #fffdf8; border: 1px solid #ded2c2;
                border-radius: 7px; padding: 6px; color: #332d27;
            }
            QPushButton { background: #e9a86c; color: #30251c; border: 0;
                          border-radius: 8px; padding: 7px 10px; }
            QPushButton:hover { background: #f0b77f; }
            QPushButton:disabled { background: #ded7cc; color: #756e64; }
            QPushButton#secondaryButton { background: #eee7dc; }
            QFrame#taskRow { background: #fffdf8; border: 1px solid #eadfca;
                             border-radius: 10px; }
            QProgressBar { background: #eee7dc; border: 0; border-radius: 6px;
                           height: 12px; text-align: center; }
            QProgressBar::chunk { background: #91b887; border-radius: 6px; }
            QScrollArea { border: 0; background: transparent; }
        """)

        self.card = QFrame(self)
        self.card.setObjectName("card")
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(15, 12, 15, 14)
        layout.setSpacing(9)

        title_bar = DragBar(self)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        self.name_heading = QLabel()
        self.name_heading.setStyleSheet("font-size: 16px; font-weight: 700;")
        close = QPushButton("×")
        close.setFixedWidth(30)
        close.clicked.connect(self.close)
        title_layout.addWidget(self.name_heading)
        title_layout.addStretch()
        title_layout.addWidget(close)
        layout.addWidget(title_bar)

        pet_row = QHBoxLayout()
        self.pet = QLabel()
        self.pet.setObjectName("pet")
        self.pet.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pet_row.addWidget(self.pet)
        self.mood_message = QLabel()
        self.mood_message.setObjectName("status")
        self.mood_message.setWordWrap(True)
        pet_row.addWidget(self.mood_message, 1)
        layout.addLayout(pet_row)

        mood_header = QHBoxLayout()
        mood_header.addWidget(QLabel("Mood"))
        mood_header.addStretch()
        self.mood_value = QLabel()
        mood_header.addWidget(self.mood_value)
        layout.addLayout(mood_header)
        self.mood_bar = QProgressBar()
        self.mood_bar.setRange(0, 100)
        self.mood_bar.setTextVisible(False)
        layout.addWidget(self.mood_bar)

        layout.addWidget(self.section_label("Personalize your dog"))
        settings_row = QHBoxLayout()
        self.name_input = QLineEdit(self.state["name"])
        self.name_input.setPlaceholderText("Dog's name")
        self.name_input.setMaxLength(24)
        self.name_input.editingFinished.connect(self.save_name)
        settings_row.addWidget(self.name_input, 1)

        self.temperament = QComboBox()
        self.temperament.addItems(["Kind", "Sassy", "Asshole"])
        self.temperament.setCurrentText(self.state["temperament"])
        self.temperament.currentTextChanged.connect(self.save_temperament)
        settings_row.addWidget(self.temperament)
        layout.addLayout(settings_row)

        self.dog_style = QComboBox()
        self.dog_style.addItem("Classic dog", "\U0001F436")
        self.dog_style.addItem("Dog", "\U0001F415")
        self.dog_style.addItem("Poodle", "\U0001F429")
        self.dog_style.addItem("Guide dog", "\U0001F9AE")
        style_index = self.dog_style.findData(self.state["dog_style"])
        self.dog_style.setCurrentIndex(max(style_index, 0))
        self.dog_style.currentIndexChanged.connect(self.save_dog_style)
        layout.addWidget(self.dog_style)

        layout.addWidget(self.section_label("Today's tasks"))
        add_row = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("What do you want to do?")
        self.task_input.returnPressed.connect(self.add_task)
        add_row.addWidget(self.task_input, 1)
        self.deadline_input = QTimeEdit()
        self.deadline_input.setDisplayFormat("h:mm AP")
        self.deadline_input.setTime(QTime.currentTime().addSecs(60 * 60))
        self.deadline_input.setToolTip("Choose today's deadline for this task")
        add_row.addWidget(self.deadline_input)
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_task)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

        self.task_list = QWidget()
        self.task_list_layout = QVBoxLayout(self.task_list)
        self.task_list_layout.setContentsMargins(0, 0, 0, 0)
        self.task_list_layout.setSpacing(6)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMaximumHeight(230)
        self.scroll.setWidget(self.task_list)
        layout.addWidget(self.scroll)

        self.feedback = QLabel("")
        self.feedback.setObjectName("status")
        layout.addWidget(self.feedback)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.card)

        self.render_tasks()
        self.refresh_view()
        self.save_state()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(60_000)

    @staticmethod
    def section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-weight: 700; margin-top: 3px;")
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
        if not isinstance(state.get("tasks"), list):
            state["tasks"] = []
        state["tasks"] = [
            task for task in state["tasks"]
            if isinstance(task, dict) and task.get("title") and task.get("deadline")
        ]
        for task in state["tasks"]:
            task.setdefault("id", str(uuid.uuid4()))
            task.setdefault("done", False)
        try:
            state["mood"] = max(0.0, min(100.0, float(state["mood"])))
        except (TypeError, ValueError):
            state["mood"] = 100.0
        return state

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
        for task in self.state["tasks"]:
            task["done"] = False
        self.state["mood"] = 100.0
        self.state["mood_frozen"] = False
        self.state["mood_updated_at"] = datetime.now().isoformat()
        self.save_state()

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
        self.task_list_layout.addStretch(1)

    def add_task(self) -> None:
        title = self.task_input.text().strip()
        if not title:
            self.task_input.setFocus()
            return

        self.update_mood()
        self.state["tasks"].append({
            "id": str(uuid.uuid4()),
            "title": title,
            "deadline": self.deadline_input.time().toString("HH:mm"),
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

        answer = QMessageBox.question(
            self,
            "Confirm task",
            f"Have you completed this task?\n\n{task['title']}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.No:
            QMessageBox.information(
                self, "Not yet", "Come back when you finish the task."
            )
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

    def closeEvent(self, event) -> None:
        self.update_mood()
        self.save_state()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setOrganizationName("WilsonDogSelfHelp")
    app.setApplicationName("Wilson")
    widget = PetWidget()
    widget.move(80, 100)
    widget.show()
    sys.exit(app.exec())
