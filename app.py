from __future__ import annotations

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)


class PetWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Daily Dog")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(280)

        self.card = QFrame(self)
        self.card.setObjectName("card")
        self.card.setStyleSheet("""
            QFrame#card { background: #fffaf0; border: 1px solid #eadfca;
                          border-radius: 18px; }
            QLabel { color: #332d27; }
            QCheckBox { color: #332d27; spacing: 8px; }
            QPushButton { background: #e9a86c; color: #30251c; border: 0;
                          border-radius: 9px; padding: 7px 12px; }
            QPushButton:hover { background: #f0b77f; }
        """)
        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(9)

        header = QHBoxLayout()
        title = QLabel("Daily Dog")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        close = QPushButton("×")
        close.setFixedWidth(30)
        close.clicked.connect(self.close)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close)
        layout.addLayout(header)

        self.pet = QLabel("🐶")
        self.pet.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pet.setStyleSheet("font-size: 54px; padding: 2px;")
        layout.addWidget(self.pet)

        self.mood = QLabel("Ready for a good day!")
        self.mood.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mood)

        self.tasks = [
            QCheckBox("Take a short walk"),
            QCheckBox("Read for 15 minutes"),
            QCheckBox("Tidy one small area"),
        ]
        for task in self.tasks:
            task.stateChanged.connect(self.refresh_pet)
            layout.addWidget(task)

        self.progress = QLabel()
        self.progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress)
        self.refresh_pet()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.card)

        self._drag_offset = None

    def refresh_pet(self) -> None:
        done = sum(task.isChecked() for task in self.tasks)
        self.progress.setText(f"{done} of {len(self.tasks)} goals done")
        if done == len(self.tasks):
            self.pet.setText("🐕‍🦺")
            self.mood.setText("You did it! Great work!")
        elif done:
            self.pet.setText("🐶")
            self.mood.setText("Nice progress. Keep going!")
        else:
            self.pet.setText("🐕")
            self.mood.setText("Ready for a good day!")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = PetWidget()
    widget.move(80, 100)
    widget.show()
    sys.exit(app.exec())
