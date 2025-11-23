"""Reusable base widgets for detail and list views."""

from abc import ABCMeta, abstractmethod
from typing import Any

import qtawesome as qta
from PySide6.QtCore import QObject, QSize, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


# Métaclasse combinée pour résoudre le conflit entre QWidget et ABC
class QABCMeta(type(QWidget), ABCMeta):
    """Combined metaclass allowing the use of ABC with QWidget."""

    pass


class ClickableLabel(QLabel):
    """Label that emits a signal on double-click."""

    double_clicked = Signal()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class BaseDetailWidget(QWidget, metaclass=QABCMeta):
    """Base class for detail widgets (Customer, Article, etc.).

    Provides common structure: avatar, editable fields, action buttons,
    validation, and edit mode management.
    """

    # Signals to override in subclasses
    item_saved = Signal(object)
    editing_changed = Signal(bool)
    item_deleted = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_id = None
        self._fields = {}  # Dict[str, tuple[ClickableLabel, QLineEdit, QLabel]]

        # Set white background using QPalette
        from PySide6.QtGui import QPalette

        pal = QPalette()
        pal.setColor(QPalette.Window, Qt.white)
        pal.setColor(QPalette.Base, Qt.white)
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        # === Avatar ===
        self._avatar = QLabel()
        self._avatar.setFixedSize(96, 96)
        self._avatar.setAlignment(Qt.AlignCenter)

        # Main layout
        content_layout = QHBoxLayout()
        content_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Left column: avatar
        self._left_col = QVBoxLayout()
        self._left_col.setSpacing(4)  # Reduced spacing between avatar and button
        self._left_col.addWidget(self._avatar, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # Add edit button under avatar
        icon_color = "#444444"
        self._edit_btn = QPushButton()
        self._edit_btn.setIcon(qta.icon("fa5s.edit", color=icon_color))
        self._edit_btn.setIconSize(QSize(16, 16))
        self._edit_btn.setFixedSize(32, 32)
        self._edit_btn.setToolTip("Edit")
        self._edit_btn.setEnabled(False)
        self._left_col.addWidget(self._edit_btn, alignment=Qt.AlignHCenter)
        self._left_col.addStretch()  # Push avatar and button to top

        # Right column: fields (to be filled by subclasses)
        self._right_col = QVBoxLayout()
        self._right_col.setSpacing(2)  # Reduced spacing between widgets

        # Action buttons (except edit which is under avatar)
        self._save_btn = QPushButton()
        self._save_btn.setIcon(qta.icon("fa5s.save", color=icon_color))
        self._save_btn.setIconSize(QSize(16, 16))
        self._save_btn.setFixedSize(32, 32)
        self._save_btn.setToolTip("Save")
        self._delete_btn = QPushButton()
        self._delete_btn.setIcon(qta.icon("fa5s.trash", color=icon_color))
        self._delete_btn.setIconSize(QSize(16, 16))
        self._delete_btn.setFixedSize(32, 32)
        self._delete_btn.setToolTip("Delete")
        self._cancel_btn = QPushButton()
        self._cancel_btn.setIcon(qta.icon("fa5s.times", color=icon_color))
        self._cancel_btn.setIconSize(QSize(16, 16))
        self._cancel_btn.setFixedSize(32, 32)
        self._cancel_btn.setToolTip("Cancel")
        self._save_btn.setVisible(False)
        self._save_btn.setEnabled(False)
        self._cancel_btn.setVisible(False)
        # The delete button remains visible but disabled by default
        self._delete_btn.setEnabled(False)

        self._actions_layout = QHBoxLayout()
        self._actions_layout.addStretch()
        self._actions_layout.addWidget(self._save_btn)
        self._actions_layout.addWidget(self._cancel_btn)

        content_layout.addLayout(self._left_col, 0)
        content_layout.addLayout(self._right_col, 0)
        content_layout.addStretch()  # Add stretch to push content to the left
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.addLayout(content_layout)
        main_layout.addStretch()  # Push content to top

        # Common connections
        self._edit_btn.clicked.connect(lambda: self._enter_edit_mode(True))
        self._cancel_btn.clicked.connect(lambda: self._enter_edit_mode(False))
        self._save_btn.clicked.connect(self._save_changes)
        self._delete_btn.clicked.connect(self._on_delete_clicked)

    def _add_field(
        self, name: str, label_text: str, placeholder: str, is_primary: bool = False, word_wrap: bool = False
    ):
        """Add an editable field (label + edit + error).

        Args:
            name: Field name (key in _fields)
            label_text: Initial label text
            placeholder: Placeholder for edit field
            is_primary: If True, use large and bold font
            word_wrap: If True, enable word wrap on label
        """
        # Label cliquable
        label = ClickableLabel(label_text)
        if is_primary:
            font = QFont()
            font.setPointSize(16)
            font.setBold(True)
            label.setFont(font)
        else:
            label.setStyleSheet("color: #444444;")
        if word_wrap:
            label.setWordWrap(True)

        # Champ d'édition
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setVisible(False)

        # Label d'erreur
        error = QLabel("")
        error.setStyleSheet("color: #c00; font-size:11px;")
        error.setVisible(False)

        # Store in dictionary
        self._fields[name] = (label, edit, error)

        # Add to layout with reduced spacing
        self._right_col.addWidget(label)
        self._right_col.addWidget(edit)
        self._right_col.addWidget(error)
        # Add small spacing between fields (except for the last one)
        if not is_primary:
            self._right_col.addSpacing(4)

        # Connect double-click for editing
        label.double_clicked.connect(lambda: self._enter_edit_mode(True))

        # Connect reactive validation
        edit.textChanged.connect(self._validate_fields)

        return label, edit, error

    def _load_avatar_icon(self, icon_name: str):
        """Load avatar icon with qtawesome."""
        icon_color = "#444444"
        icon_map = {
            "customers": "fa5s.users",
            "articles": "fa5s.wine-bottle",
        }

        icon_key = icon_map.get(icon_name, "fa5s.file")
        icon = qta.icon(icon_key, color=icon_color)
        pix = icon.pixmap(QSize(96, 96))
        if not pix.isNull():
            self._avatar.setPixmap(pix)

    def _finalize_layout(self):
        """Finalize layout by adding action buttons."""
        self._right_col.addLayout(self._actions_layout)
        self._right_col.addStretch()  # Push content to top

    def _enter_edit_mode(self, editing: bool):
        """Toggle between view mode and edit mode."""
        self.editing_changed.emit(editing)

        # Show/hide widgets
        for label, edit, _error in self._fields.values():
            label.setVisible(not editing)
            edit.setVisible(editing)
            if editing:
                edit.setText(label.text())

        self._edit_btn.setVisible(not editing)
        self._save_btn.setVisible(editing)
        self._cancel_btn.setVisible(editing)

        # Delete button: always visible, enabled based on _current_id and mode
        if editing:
            # In edit mode, disable delete
            self._delete_btn.setEnabled(False)
        else:
            # In view mode, enable if we have an ID
            self._delete_btn.setEnabled(self._current_id is not None)

        if editing:
            self._validate_fields()

    @abstractmethod
    def _save_changes(self):
        """Save changes (to be implemented in subclasses)."""
        pass

    @abstractmethod
    def _on_delete_clicked(self):
        """Handle deletion (to be implemented in subclasses)."""
        pass

    @abstractmethod
    def _validate_fields(self) -> bool:
        """Validate fields (to be implemented in subclasses)."""
        pass

    def clear(self):
        """Clear all fields and reset to empty state."""
        self._current_id = None

        # Clear all field labels
        for label, edit, error in self._fields.values():
            label.setText("")
            edit.clear()
            error.setVisible(False)

        # Disable buttons
        self._edit_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        self._save_btn.setVisible(False)
        self._cancel_btn.setVisible(False)

        # Exit edit mode
        self._enter_edit_mode(False)


class SearchWorker(QObject):
    """Worker that executes searches in a separate thread."""

    results_ready = Signal(object)
    error = Signal(str)

    def __init__(self, search_func):
        """Initialize the worker with a search function.

        Args:
            search_func: Callable function(query: str, limit: int) -> list
        """
        super().__init__()
        self._search_func = search_func

    @Slot(str, int)
    def search(self, q: str, limit: int):
        try:
            rows = self._search_func(q, limit=limit)
            self.results_ready.emit(rows)
        except Exception as e:
            self.error.emit(str(e))
            self.results_ready.emit([])


class BaseListView(QWidget, metaclass=QABCMeta):
    """Base class for views with list and detail (Customers, Articles, etc.).

    Provides: search with debounce, list, detail, and CRUD management.
    """

    item_selected = Signal(object)
    search_requested = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Background search worker configuration
        self._search_thread = QThread(self)
        self._search_worker = SearchWorker(self._search_function)
        self._search_worker.moveToThread(self._search_thread)
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.error.connect(lambda e: print(f"[search error] {e}"))
        self.search_requested.connect(self._search_worker.search)
        self._search_thread.start()

        # Timer for search debounce
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._perform_search)

        # Splitter to separate list and detail
        self._splitter = QSplitter(Qt.Horizontal, self)

        # === Left column: search and list ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(self._search_placeholder())
        # Add search icon
        icon_color = "#444444"
        self.search_box.addAction(qta.icon("fa5s.search", color=icon_color), QLineEdit.LeadingPosition)

        self._results_count_label = QLabel("")
        self._results_count_label.setStyleSheet("color: #666; font-size:11px; padding:4px 0;")
        self._results_count_label.setAlignment(Qt.AlignRight)

        self._results_list = QListWidget()
        self._results_list.setSelectionMode(QListWidget.SingleSelection)

        left_layout.addWidget(self.search_box)
        left_layout.addWidget(self._results_count_label)
        left_layout.addWidget(self._results_list, 1)

        # === Right column: detail (to be created in subclasses) ===
        self._detail_widget = self._create_detail_widget()

        # Create white container for detail widget
        right_container = QWidget()
        right_container.setStyleSheet("background-color: white;")
        right_container_layout = QVBoxLayout(right_container)
        right_container_layout.setContentsMargins(0, 0, 0, 0)
        right_container_layout.addWidget(self._detail_widget)

        # Buttons under list (aligned to right: new then delete)
        list_buttons_layout = QHBoxLayout()
        list_buttons_layout.addStretch()
        self._add_btn = QPushButton()
        self._add_btn.setIcon(qta.icon("fa5s.plus", color=icon_color))
        self._add_btn.setIconSize(QSize(16, 16))
        self._add_btn.setFixedSize(32, 32)
        self._add_btn.setToolTip("New")
        list_buttons_layout.addWidget(self._add_btn)
        list_buttons_layout.addWidget(self._detail_widget._delete_btn)

        left_layout.addLayout(list_buttons_layout)

        # Add widgets to splitter
        self._splitter.addWidget(left_widget)
        self._splitter.addWidget(right_container)

        # Set fixed initial size for left column and allow resizing
        self._splitter.setStretchFactor(0, 0)  # Left column doesn't stretch
        self._splitter.setStretchFactor(1, 1)  # Right column takes remaining space
        self._splitter.setSizes([300, 500])  # Initial size: 300px for list, 500px for detail

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._splitter)

        # === Signal connections ===
        self._detail_widget.item_saved.connect(self._on_saved)
        self._detail_widget.item_deleted.connect(self._on_deleted)
        self.search_box.textChanged.connect(self._on_search_text_changed)
        self._results_list.itemActivated.connect(self._on_item_activated)
        self._results_list.itemClicked.connect(self._on_item_activated)
        self._results_list.currentItemChanged.connect(lambda cur, prev: self._on_item_activated(cur) if cur else None)
        self._add_btn.clicked.connect(self._on_add_item)

        # Load initial data after complete initialization
        QTimer.singleShot(0, self.reload_items)

    @abstractmethod
    def _search_placeholder(self) -> str:
        """Return the placeholder for the search field."""
        pass

    @abstractmethod
    def _search_function(self):
        """Return the search function to use."""
        pass

    @abstractmethod
    def _create_detail_widget(self) -> BaseDetailWidget:
        """Create and return the detail widget."""
        pass

    @abstractmethod
    def _get_all_items(self) -> list:
        """Retrieve all items from the database."""
        pass

    @abstractmethod
    def _format_list_item(self, item: Any) -> str:
        """Format an item for display in the list."""
        pass

    @abstractmethod
    def _on_saved(self, data: dict):
        """Handle item save."""
        pass

    @abstractmethod
    def _on_deleted(self, item_id: int | None):
        """Handle item deletion."""
        pass

    def _on_search_text_changed(self, text: str):
        """Restart debounce timer when user types."""
        if not text or not text.strip():
            self._search_timer.stop()
            self.reload_items()
        else:
            self._search_timer.start()

    def _perform_search(self):
        """Execute search via background worker."""
        q = self.search_box.text().strip()
        if not q:
            self.reload_items()
        else:
            self.search_requested.emit(q, 50)

    def _on_search_results(self, rows: list):
        """Handle search results from worker."""
        max_shown = 50
        rows_limited = rows[:max_shown]

        self._results_list.clear()
        for item in rows_limited:
            disp = self._format_list_item(item)
            list_item = QListWidgetItem(disp)
            list_item.setData(Qt.ItemDataRole.UserRole, item)  # Store complete object
            self._results_list.addItem(list_item)

        # Select first result
        if self._results_list.count() > 0:
            self._results_list.setCurrentRow(0)
            self._on_item_activated(self._results_list.item(0))
        else:
            # No results: disable delete button
            self._detail_widget._delete_btn.setEnabled(False)

        # Update counter
        try:
            total = len(self._get_all_items())
            shown = len(rows_limited)
            self._results_count_label.setText(f"{shown} / {total} résultats")
        except Exception:
            self._results_count_label.setText("")

    def reload_items(self, select_first: bool = True):
        """Reload item list from database."""
        try:
            items = self._get_all_items()
        except Exception:
            items = []

        self._results_list.clear()
        for item in items:
            disp = self._format_list_item(item)
            list_item = QListWidgetItem(disp)
            list_item.setData(Qt.ItemDataRole.UserRole, item)  # Store complete object
            self._results_list.addItem(list_item)

        total = len(items)
        shown = min(total, 50)
        self._results_count_label.setText(f"{shown} / {total} results")

        if select_first and self._results_list.count() > 0:
            first_item = self._results_list.item(0)
            self._results_list.setCurrentRow(0)
            if first_item:
                self._on_item_activated(first_item)
        elif self._results_list.count() == 0:
            # No item: clear detail widget and disable delete button
            if hasattr(self._detail_widget, "clear"):
                self._detail_widget.clear()
            self._detail_widget._delete_btn.setEnabled(False)

    @abstractmethod
    def _on_item_activated(self, item: QListWidgetItem):
        """Handle item selection in the list."""
        pass

    @abstractmethod
    def _on_add_item(self):
        """Create an empty item and open editor."""
        pass

    def cleanup(self):
        """Clean up resources (search thread)."""
        if hasattr(self, "_search_thread") and self._search_thread.isRunning():
            self._search_thread.quit()
            self._search_thread.wait(1000)
