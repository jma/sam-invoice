from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def validate_customer_fields(name: str, address: str) -> tuple[bool, str | None]:
    """Validate customer fields.

    Returns (True, None) if valid, otherwise (False, error_message).
    Requires name and address to be at least 3 characters long (after strip).
    """
    n = (name or "").strip()
    a = (address or "").strip()
    if not n:
        return False, "Name is required"
    if len(n) < 3:
        return False, "Name must be at least 3 characters"
    if not a:
        return False, "Address is required"
    if len(a) < 3:
        return False, "Address must be at least 3 characters"
    return True, None


class ClickableLabel(QLabel):
    """A QLabel that emits a signal on double-click for in-place editing."""

    double_clicked = Signal()

    def mouseDoubleClickEvent(self, event):
        try:
            self.double_clicked.emit()
        finally:
            super().mouseDoubleClickEvent(event)


class CustomerDetailWidget(QWidget):
    """Improved detail widget with large avatar and prominent name.

    Supports inline editing and emits `customer_saved` with a dict when saved.
    """

    customer_saved = Signal(object)
    editing_changed = Signal(bool)
    customer_deleted = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_id = None

        # Large avatar/icon on the left
        self._avatar = QLabel()
        self._avatar.setFixedSize(96, 96)
        self._avatar.setAlignment(Qt.AlignCenter)

        # Name with larger font (label + editor)
        self._name = ClickableLabel("")
        name_font = QFont()
        name_font.setPointSize(16)
        name_font.setBold(True)
        self._name.setFont(name_font)
        self._name_edit = QLineEdit()
        self._name_edit.setVisible(False)

        # validation label for name
        self._name_err = QLabel("")
        self._name_err.setStyleSheet("color: #c00; font-size:11px;")
        self._name_err.setVisible(False)
        # Secondary details (label + editor)
        self._address = ClickableLabel("")
        self._email = ClickableLabel("")
        self._address.setWordWrap(True)
        self._email.setWordWrap(True)
        self._address.setStyleSheet("color: #444444;")
        self._email.setStyleSheet("color: #444444;")

        self._address_edit = QLineEdit()
        self._address_edit.setVisible(False)
        self._email_edit = QLineEdit()
        self._email_edit.setVisible(False)

        # placeholders to guide the user while editing
        try:
            self._name_edit.setPlaceholderText("e.g. John Doe")
            self._address_edit.setPlaceholderText("e.g. 1 Wine St, Apt 2")
            self._email_edit.setPlaceholderText("e.g. name@example.com")
        except Exception:
            pass

        # reactive validation while editing
        self._name_edit.textChanged.connect(lambda *_: self._validate_fields())
        self._address_edit.textChanged.connect(lambda *_: self._validate_fields())

        # two-column layout: left avatar, right fields (name, email, address)
        # validation label for address
        self._address_err = QLabel("")
        self._address_err.setStyleSheet("color: #c00; font-size:11px;")
        self._address_err.setVisible(False)
        content_layout = QHBoxLayout()
        # ensure the whole content is aligned to the top of the widget
        content_layout.setAlignment(Qt.AlignTop)

        left_col = QVBoxLayout()
        # place avatar at the top and horizontally centered
        left_col.addWidget(self._avatar, alignment=Qt.AlignHCenter | Qt.AlignTop)

        right_col = QVBoxLayout()

        # Name row (label + editor)
        right_col.addWidget(self._name)
        right_col.addWidget(self._name_edit)

        # Secondary validation label then Address row followed by Email
        right_col.addWidget(self._name_err)

        # Address row (multi-line label + single-line editor)
        right_col.addWidget(self._address)
        right_col.addWidget(self._address_edit)
        # validation label for address placed directly under the address editor
        right_col.addWidget(self._address_err)

        # Email row
        right_col.addWidget(self._email)
        right_col.addWidget(self._email_edit)

        # small action row (Edit -> Save / Cancel) aligned to the right
        self._edit_btn = QPushButton("Edit")
        self._save_btn = QPushButton("Save")
        self._delete_btn = QPushButton("Delete")
        self._cancel_btn = QPushButton("Cancel")
        self._save_btn.setVisible(False)
        self._cancel_btn.setVisible(False)
        self._edit_btn.setEnabled(False)
        self._delete_btn.setVisible(False)

        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        actions_layout.addWidget(self._edit_btn)
        actions_layout.addWidget(self._delete_btn)
        actions_layout.addWidget(self._save_btn)
        actions_layout.addWidget(self._cancel_btn)

        right_col.addLayout(actions_layout)

        content_layout.addLayout(left_col, 1)
        content_layout.addLayout(right_col, 3)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(content_layout)

        # try to prepare an avatar icon from package assets
        icons_dir = Path(__file__).parent.parent / "assets" / "icons"
        avatar_path = icons_dir / "customers.svg"
        if avatar_path.exists():
            icon = QIcon(str(avatar_path))
            pix = icon.pixmap(QSize(96, 96))
            if not pix.isNull():
                self._avatar.setPixmap(pix)

        # animation effect
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)

        # connections
        self._edit_btn.clicked.connect(lambda: self._enter_edit_mode(True))
        self._cancel_btn.clicked.connect(lambda: self._enter_edit_mode(False))
        self._save_btn.clicked.connect(self._save_changes)

        # enable in-place editing by double-clicking labels
        try:
            self._name.double_clicked.connect(lambda: self._enter_edit_mode(True))
            self._address.double_clicked.connect(lambda: self._enter_edit_mode(True))
            self._email.double_clicked.connect(lambda: self._enter_edit_mode(True))
        except Exception:
            pass

        # hide the Edit button when using in-place editing
        self._edit_btn.setVisible(False)

        # ensure Save is disabled by default until fields are valid
        try:
            self._save_btn.setEnabled(False)
        except Exception:
            pass

        # fallback callback (in case Signals are not available or fail)
        self._saved_callback = None
        # fallback for editing state changes
        self._editing_callback = None
        # fallback for delete
        self._deleted_callback = None

        # connect delete button handler
        try:
            self._delete_btn.clicked.connect(self._on_delete_clicked)
        except Exception:
            pass

    def register_saved_callback(self, cb):
        """Register a plain-Python callback as fallback for saved events.

        The callback will be called with a single argument: the data dict.
        """
        self._saved_callback = cb

    def register_editing_callback(self, cb):
        """Register a plain-Python callback as fallback when editing starts/stops.

        The callback will be called with a single bool argument: True when entering
        edit mode, False when leaving it.
        """
        self._editing_callback = cb

    def register_deleted_callback(self, cb):
        """Register a plain-Python callback as fallback for delete events.

        The callback will be called with a single argument: the customer id (int).
        """
        self._deleted_callback = cb

    def _animate(self, start: float, end: float, duration: int = 220):
        anim = QPropertyAnimation(self._effect, b"opacity", self)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()

    def _enter_edit_mode(self, editing: bool):
        # notify listeners about editing state change (Signal preferred)
        try:
            self.editing_changed.emit(editing)
        except Exception:
            if self._editing_callback:
                try:
                    self._editing_callback(editing)
                except Exception:
                    pass

        # animate fade out -> toggle -> fade in
        self._animate(1.0, 0.0, duration=120)
        # toggle widgets after a short delay (animation still running but quick)
        self._name.setVisible(not editing)
        self._name_edit.setVisible(editing)
        self._email.setVisible(not editing)
        self._email_edit.setVisible(editing)
        self._address.setVisible(not editing)
        self._address_edit.setVisible(editing)
        self._edit_btn.setVisible(not editing)
        self._save_btn.setVisible(editing)
        self._cancel_btn.setVisible(editing)
        # show delete only when not editing and a customer is loaded
        try:
            self._delete_btn.setVisible(not editing and self._current_id is not None)
        except Exception:
            pass
        # populate editors with current text when entering
        if editing:
            self._name_edit.setText(self._name.text())
            self._email_edit.setText(self._email.text())
            self._address_edit.setText(self._address.text())
            # ensure validation state is applied when entering
            try:
                self._validate_fields()
            except Exception:
                pass
        self._animate(0.0, 1.0, duration=220)

    def _save_changes(self):
        # build data and emit
        data = {
            "id": self._current_id,
            "name": self._name_edit.text().strip(),
            "address": self._address_edit.text().strip(),
            "email": self._email_edit.text().strip(),
        }
        # emit PySide signal if available
        try:
            self.customer_saved.emit(data)
        except Exception:
            # fallback to plain callback if provided
            if self._saved_callback:
                try:
                    self._saved_callback(data)
                except Exception:
                    pass
        self._enter_edit_mode(False)

    def _on_delete_clicked(self):
        cid = getattr(self, "_current_id", None)
        if cid is None:
            return
        name = self._name.text() or ""
        res = QMessageBox.question(
            self,
            "Delete",
            f"Delete customer '{name}'? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return
        try:
            # emit signal with id
            try:
                self.customer_deleted.emit(int(cid))
            except Exception:
                if self._deleted_callback:
                    try:
                        self._deleted_callback(int(cid))
                    except Exception:
                        pass
        except Exception:
            pass

    def _validate_fields(self) -> bool:
        """Simple validation: name and address are required and at least 3 chars."""
        try:
            name = (self._name_edit.text() or "").strip()
            address = (self._address_edit.text() or "").strip()
            valid = True
            # name validation
            if not name:
                self._name_err.setText("Name is required")
                self._name_err.setVisible(True)
                valid = False
            elif len(name) < 3:
                self._name_err.setText("Name must be at least 3 characters")
                self._name_err.setVisible(True)
                valid = False
            else:
                self._name_err.setVisible(False)

            # address validation
            if not address:
                self._address_err.setText("Address is required")
                self._address_err.setVisible(True)
                valid = False
            elif len(address) < 3:
                self._address_err.setText("Address must be at least 3 characters")
                self._address_err.setVisible(True)
                valid = False
            else:
                self._address_err.setVisible(False)
            try:
                self._save_btn.setEnabled(valid)
            except Exception:
                pass
            return valid
        except Exception:
            try:
                self._save_btn.setEnabled(False)
            except Exception:
                pass
            return False

    def set_customer(self, cust):
        self._current_id = getattr(cust, "id", None) if cust else None
        if not cust:
            self._name.setText("")
            self._address.setText("")
            self._email.setText("")
            self._edit_btn.setEnabled(False)
            # hide edit/delete when no customer is loaded
            try:
                self._edit_btn.setVisible(False)
                self._delete_btn.setVisible(False)
            except Exception:
                pass
            return
        self._name.setText(getattr(cust, "name", ""))
        self._address.setText(getattr(cust, "address", ""))
        self._email.setText(getattr(cust, "email", ""))
        self._edit_btn.setEnabled(True)
        # make edit visible and show delete when there is a persisted id
        try:
            self._edit_btn.setVisible(True)
            self._delete_btn.setVisible(self._current_id is not None)
        except Exception:
            pass

    def edit_button(self):
        return self._edit_btn
