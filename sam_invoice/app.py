import os
import signal
import sys
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QObject, QSize, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

import sam_invoice.models.crud_customer as crud
from sam_invoice.ui.customer_detail import CustomerDetailWidget


class SearchWorker(QObject):
    """Worker that runs database searches in a background thread."""

    results_ready = Signal(object)
    error = Signal(str)

    @Slot(str, int)
    def search(self, q: str, limit: int):
        try:
            rows = crud.search_customers(q, limit=limit)
            # ensure alphabetical order by name as a safeguard
            rows = sorted(rows, key=lambda c: (getattr(c, "name", "") or "").lower())
            self.results_ready.emit(rows)
        except Exception as e:
            self.error.emit(str(e))
            try:
                self.results_ready.emit([])
            except Exception:
                pass


class MainWindow(QMainWindow):
    # signal used to request a background search (emitted from the UI thread)
    search_requested = Signal(str, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sam Invoice")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        header = QLabel("Sam Invoice — Main")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size:18pt; font-weight:600; padding:8px;")
        main_layout.addWidget(header)

        # Tool bar with Home / Customers / Invoices actions
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        # On macOS, prefer a unified title bar and toolbar like native apps
        if sys.platform == "darwin":
            try:
                # QMainWindow provides setUnifiedTitleAndToolBarOnMac
                self.setUnifiedTitleAndToolBarOnMac(True)
            except Exception:
                pass
        # try to load bundled SVG icons (located inside the package),
        # fallback to standard icons if missing
        base = Path(__file__).parent / "assets" / "icons"
        if not base.exists():
            # helpful debug when running locally or in CI
            print(f"[sam_invoice] icons folder not found: {base}")

        def load_icon(name: str, fallback: QStyle.StandardPixmap):
            p = (base / f"{name}.svg").resolve()
            if p.exists():
                return QIcon(str(p))
            return self.style().standardIcon(fallback)

        home_icon = load_icon("home", QStyle.SP_DirHomeIcon)
        # customers view removed; only keep home and invoices icons
        invoices_icon = load_icon("invoices", QStyle.SP_FileIcon)

        # actions (checkable so we can show active state)
        self.act_home = QAction(home_icon, "Home", self)
        self.act_home.setCheckable(True)
        # no Customers action (removed)
        self.act_invoices = QAction(invoices_icon, "Invoices", self)
        self.act_invoices.setCheckable(True)

        # prepare active (colored) variants of the icons (light blue)
        def colorize_icon(icon: QIcon, color: QColor, size: QSize | None = None) -> QIcon:
            if size is None:
                size = QSize(48, 48)
            pix = icon.pixmap(size)
            if pix.isNull():
                return icon
            colored = QPixmap(pix.size())
            colored.fill(Qt.transparent)
            p = QPainter(colored)
            p.fillRect(colored.rect(), color)
            p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            p.drawPixmap(0, 0, pix)
            p.end()
            return QIcon(colored)

        active_color = QColor("#3b82f6")  # light blue
        home_icon_active = colorize_icon(home_icon, active_color)
        invoices_icon_active = colorize_icon(invoices_icon, active_color)
        # store normal/active pairs for switching
        self._icon_pairs = {
            self.act_home: (home_icon, home_icon_active),
            self.act_invoices: (invoices_icon, invoices_icon_active),
        }

        # show text under icons for clarity
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.addAction(self.act_home)
        # customers action removed
        toolbar.addAction(self.act_invoices)

        # add toolbar to the main window (appears above central widget)
        self.addToolBar(toolbar)

        # Stacked area for views
        self.stack = QStackedWidget()
        # Home page placeholder
        home_widget = QWidget()
        home_layout = QVBoxLayout(home_widget)

        # Search box for customers (results shown in the left-hand list)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Rechercher un client (nom, email)...")
        # label showing number of displayed results / total in DB
        self._results_count_label = QLabel("")
        self._results_count_label.setStyleSheet("color: #666; font-size:11px; padding:4px 0;")
        # results are shown in the left-hand list

        # mapping display -> id
        self._customer_map = {}

        # timer used to debounce live DB searches while typing
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)  # ms
        self._search_timer.timeout.connect(self._perform_live_search)

        # connect live search on text change (debounced)
        self.search_box.textChanged.connect(self._on_search_text_changed)

        # Setup background search worker/thread to avoid blocking UI
        self._search_thread = QThread(self)
        self._search_worker = SearchWorker()
        self._search_worker.moveToThread(self._search_thread)
        # connect signal from worker to handler
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.error.connect(lambda e: print(f"[sam_invoice] search worker error: {e}"))
        # wire the MainWindow.search_requested signal to the worker.search slot
        self.search_requested.connect(self._search_worker.search)
        self._search_thread.start()

        # create results list (left column) and detail (right column)
        self._results_list = QListWidget()
        self._results_list.setSelectionMode(QListWidget.SingleSelection)
        # make the results list expand to push the Add button to the bottom
        try:
            self._results_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass

        # placeholder where selected customer detail will be shown
        self._home_detail = CustomerDetailWidget()

        # two-column layout for home: left = search + results, right = detail
        content_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.search_box)
        left_layout.addWidget(self._results_count_label)
        # let the results list take the available vertical space (stretch=1)
        left_layout.addWidget(self._results_list, 1)
        # Add button placed after the list without stretch so it's at the bottom
        self._add_btn = QPushButton("Add")
        left_layout.addWidget(self._add_btn)
        content_layout.addLayout(left_layout, 1)
        # vertical separator between list and detail view
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        content_layout.addWidget(sep)
        content_layout.addWidget(self._home_detail, 2)
        # add the two-column content to the home layout
        home_layout.addLayout(content_layout)
        # current customer shown in home detail
        self._current_home_customer = None
        # listen to inline-save from home detail widget
        # Prefer Qt Signal, fall back to plain callback registration if needed.
        if hasattr(self._home_detail, "customer_saved"):
            try:
                self._home_detail.customer_saved.connect(self._on_home_saved)
            except Exception:
                # ignore and try fallback
                pass
        if hasattr(self._home_detail, "register_saved_callback"):
            try:
                self._home_detail.register_saved_callback(self._on_home_saved)
            except Exception:
                pass

        # listen to delete signal from the detail widget
        if hasattr(self._home_detail, "customer_deleted"):
            try:
                self._home_detail.customer_deleted.connect(self._on_home_deleted)
            except Exception:
                pass
        if hasattr(self._home_detail, "register_deleted_callback"):
            try:
                self._home_detail.register_deleted_callback(self._on_home_deleted)
            except Exception:
                pass

        # When the detail widget enters edit mode, disable the search prompt.
        if hasattr(self._home_detail, "editing_changed"):
            try:
                # keep existing behavior (disable search while editing)
                self._home_detail.editing_changed.connect(lambda editing: self.search_box.setEnabled(not editing))
                # also handle cancel case: when editing stops on a transient customer, select first list item
                self._home_detail.editing_changed.connect(self._on_editing_changed)
            except Exception:
                pass
        if hasattr(self._home_detail, "register_editing_callback"):
            try:
                # register a combined callback for fallback path
                def _editing_cb(editing: bool):
                    try:
                        self.search_box.setEnabled(not editing)
                    except Exception:
                        pass
                    try:
                        self._on_editing_changed(editing)
                    except Exception:
                        pass

                self._home_detail.register_editing_callback(_editing_cb)
            except Exception:
                pass

        # customers view removed; invoices placeholder used instead

        # invoices placeholder
        invoices_placeholder = QWidget()
        ph_layout = QVBoxLayout(invoices_placeholder)
        ph_label = QLabel("Invoices view (coming soon)")
        ph_label.setAlignment(Qt.AlignCenter)
        ph_layout.addWidget(ph_label)

        # add pages to the stack: home, invoices
        self.stack.addWidget(home_widget)
        self.stack.addWidget(invoices_placeholder)

        main_layout.addWidget(self.stack)

        # status label
        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status)

        # Display the currently applied Qt style for quick visual confirmation
        try:
            style_name = QApplication.instance().style().objectName()
        except Exception:
            style_name = "unknown"
        self.status.setText(f"Style: {style_name}")

        self.setCentralWidget(central_widget)

        # Connect toolbar actions and maintain single-active behavior
        self.act_home.triggered.connect(lambda: self._set_active(self.act_home) or self.on_home_clicked())
        # customers action removed; only Home and Invoices remain
        self.act_invoices.triggered.connect(lambda: self._set_active(self.act_invoices) or self.on_invoices_clicked())
        # default active is Home
        self._set_active(self.act_home)

        # prepare list selection handling
        self._results_list.itemActivated.connect(lambda it: self._on_result_item_activated(it))
        self._results_list.itemClicked.connect(lambda it: self._on_result_item_activated(it))
        # also update detail view when current item changes (arrow keys, programmatic selection)
        try:
            self._results_list.currentItemChanged.connect(lambda cur, prev: self._on_result_item_activated(cur))
        except Exception:
            pass
        # load customers initially
        self._reload_customer_autocomplete()

        # connect Add button to create an empty customer and open editor
        try:
            self._add_btn.clicked.connect(self._on_add_customer)
        except Exception:
            pass

    def _reload_customer_autocomplete(self, select_first: bool = True):
        """Load customer suggestions into the left-hand results list."""
        try:
            customers = list(crud.get_customers())
        except Exception:
            customers = []
        # Ensure alphabetical order by name (case-insensitive) for the UI list
        try:
            customers = sorted(customers, key=lambda c: (getattr(c, "name", "") or "").lower())
        except Exception:
            pass
        display = []
        self._customer_map.clear()
        for c in customers:
            # display like: "Name — Address" (no id, no email)
            name = (getattr(c, "name", "") or "").strip()
            address = (getattr(c, "address", "") or "").strip()
            if address:
                disp = f"{name} — {address}"
            else:
                disp = name
            display.append(disp)
            self._customer_map[disp] = getattr(c, "id", None)
        # results are shown in the left-hand list
        # also populate the left-hand results list (limit display to first N)
        max_shown = 50
        shown_display = display[:max_shown]
        try:
            self._results_list.clear()
            for disp in shown_display:
                # create an item and keep the mapping via UserRole
                try:
                    cid = self._customer_map.get(disp)
                except Exception:
                    cid = None
                item = QListWidgetItem(disp)
                try:
                    item.setData(Qt.UserRole, cid)
                except Exception:
                    pass
                self._results_list.addItem(item)
        except Exception:
            # if results list doesn't exist (older layout), ignore
            pass
        else:
            # update results count label: shown / total
            try:
                total = len(customers)
                shown = len(shown_display)
                self._results_count_label.setText(f"{shown} / {total} résultats")
            except Exception:
                try:
                    self._results_count_label.setText("")
                except Exception:
                    pass
            # optionally select the first result and show its details
            if select_first:
                try:
                    if self._results_list.count() > 0:
                        self._results_list.setCurrentRow(0)
                        item = self._results_list.item(0)
                        if item:
                            self._on_result_item_activated(item)
                except Exception:
                    pass

    def _on_search_text_changed(self, text: str) -> None:
        """Restart debounce timer when the user types in the main search box.

        If the text is empty we immediately reload the full autocomplete list.
        """
        if not text or not text.strip():
            # empty -> use full list immediately
            self._reload_customer_autocomplete()
            # ensure any pending timer is stopped
            try:
                self._search_timer.stop()
            except Exception:
                pass
            return
        # restart debounce timer
        try:
            self._search_timer.start()
        except Exception:
            # if timer failed for some reason, run search synchronously
            self._perform_live_search()

    def _perform_live_search(self) -> None:
        """Perform a DB-backed search and update completer + results list."""
        q = (self.search_box.text() or "").strip()
        if not q:
            self._reload_customer_autocomplete()
            return
        # request the background worker to perform the search (limit 100)
        try:
            # limit live search results to a reasonable number for the Home list
            self.search_requested.emit(q, 50)
        except Exception:
            # fallback to synchronous search if emitting fails
            try:
                rows = crud.search_customers(q, limit=50)
                rows = sorted(rows, key=lambda c: (getattr(c, "name", "") or "").lower())
            except Exception:
                rows = []
            self._on_search_results(rows)

    def _on_search_results(self, rows: list) -> None:
        """Handle search results emitted by the background worker and update UI."""
        # ensure we only show up to the configured max in the Home list
        max_shown = 50
        rows_limited = rows[:max_shown]
        display = []
        self._customer_map.clear()
        for c in rows_limited:
            # present only the name and address to the user
            name = (getattr(c, "name", "") or "").strip()
            address = (getattr(c, "address", "") or "").strip()
            if address:
                disp = f"{name} — {address}"
            else:
                disp = name
            display.append(disp)
            self._customer_map[disp] = getattr(c, "id", None)

        # completer removed; results are shown in the left-hand list
        try:
            self._results_list.clear()
            for disp in display:
                try:
                    cid = self._customer_map.get(disp)
                except Exception:
                    cid = None
                item = QListWidgetItem(disp)
                try:
                    item.setData(Qt.UserRole, cid)
                except Exception:
                    pass
                self._results_list.addItem(item)
            # automatically select the first result and show its details
            if self._results_list.count() > 0:
                try:
                    self._results_list.setCurrentRow(0)
                    item = self._results_list.item(0)
                    if item:
                        self._on_result_item_activated(item)
                except Exception:
                    pass
            # update results count label using total count from DB
            try:
                total = len(list(crud.get_customers()))
                shown = len(rows_limited)
                self._results_count_label.setText(f"{shown} / {total} résultats")
            except Exception:
                try:
                    self._results_count_label.setText("")
                except Exception:
                    pass
        except Exception:
            pass

    def _on_result_item_activated(self, item):
        # item can be QListWidgetItem or text
        try:
            if hasattr(item, "data"):
                cid = item.data(Qt.UserRole)
            else:
                text = item.text() if hasattr(item, "text") else str(item)
                cid = self._customer_map.get(text)
        except Exception:
            try:
                text = item.text() if hasattr(item, "text") else str(item)
                cid = self._customer_map.get(text)
            except Exception:
                cid = None
        if cid is None:
            return
        try:
            cust = crud.get_customer_by_id(int(cid))
        except Exception:
            cust = None
        self._home_detail.set_customer(cust)
        self._current_home_customer = cust
        self.stack.setCurrentIndex(0)

    def _on_add_customer(self):
        """Create an empty customer, reload list, select it and open editor on the right."""
        # create a temporary in-memory customer and open editor without persisting
        cust = SimpleNamespace(id=None, name="", address="", email="")
        try:
            self._home_detail.set_customer(cust)
            self._current_home_customer = cust
            # enter edit mode so the user can fill fields; do NOT persist yet
            try:
                enter = getattr(self._home_detail, "_enter_edit_mode", None)
                if callable(enter):
                    enter(True)
            except Exception:
                pass
            # ensure Home page is visible
            self.stack.setCurrentIndex(0)
        except Exception:
            pass

    def _on_editing_changed(self, editing: bool):
        """Handle end of editing: if we were editing a transient customer (no id), select first customer."""
        if editing:
            return
        # editing stopped
        try:
            # if current customer is transient (no id), select the first real customer
            cur = getattr(self, "_current_home_customer", None)
            cur_id = getattr(cur, "id", None) if cur is not None else None
            if cur_id is None:
                if self._results_list.count() > 0:
                    item = self._results_list.item(0)
                    if item:
                        self._results_list.setCurrentRow(0)
                        self._on_result_item_activated(item)
        except Exception:
            pass

    def closeEvent(self, event):
        """Ensure worker thread is stopped cleanly when the window closes."""
        try:
            if hasattr(self, "_search_thread") and self._search_thread.isRunning():
                self._search_thread.quit()
                self._search_thread.wait(1000)
        except Exception:
            pass
        super().closeEvent(event)

    def _on_home_saved(self, data: dict):
        """Handle inline-saved customer data from the detail widget."""
        if not data:
            return
        cid = data.get("id")
        try:
            # If id is missing, create a new customer in the DB, otherwise update existing
            if cid is None:
                new = crud.create_customer(data.get("name", ""), data.get("address", ""), data.get("email", ""))
                cid = getattr(new, "id", None)
            else:
                crud.update_customer(
                    int(cid), name=data.get("name"), address=data.get("address"), email=data.get("email")
                )
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Error", f"Failed to save customer: {e}")
            return

        # refresh autocomplete and select the saved/created customer
        try:
            self._reload_customer_autocomplete(select_first=False)
        except Exception:
            pass

        # select the item corresponding to cid if possible
        try:
            found = False
            if cid is not None:
                for i in range(self._results_list.count()):
                    it = self._results_list.item(i)
                    try:
                        if it.data(Qt.UserRole) == cid:
                            self._results_list.setCurrentRow(i)
                            found = True
                            break
                    except Exception:
                        continue
                # If the saved customer isn't among the displayed (e.g. list is limited),
                # insert it at the top of the results list so it remains visible.
                if not found:
                    try:
                        cust = crud.get_customer_by_id(int(cid)) if cid is not None else None
                    except Exception:
                        cust = None
                    if cust is not None:
                        name = (getattr(cust, "name", "") or "").strip()
                        address = (getattr(cust, "address", "") or "").strip()
                        if address:
                            disp = f"{name} — {address}"
                        else:
                            disp = name
                        item = QListWidgetItem(disp)
                        try:
                            item.setData(Qt.UserRole, cid)
                        except Exception:
                            pass
                        try:
                            self._results_list.insertItem(0, item)
                            self._results_list.setCurrentRow(0)
                        except Exception:
                            # fallback to adding at end if insert fails
                            try:
                                self._results_list.addItem(item)
                                self._results_list.setCurrentRow(self._results_list.count() - 1)
                            except Exception:
                                pass
        except Exception:
            pass

        # reload current customer and update detail from DB (use DB copy)
        try:
            cust = crud.get_customer_by_id(int(cid)) if cid is not None else None
        except Exception:
            cust = None
        self._current_home_customer = cust
        self._home_detail.set_customer(cust)

    def _on_home_deleted(self, cid: int | None):
        """Handle deletion requested from detail widget."""
        if cid is None:
            return
        try:
            crud.delete_customer(int(cid))
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Error", f"Failed to delete customer: {e}")
            return
        # refresh list and select first item if any
        try:
            self._reload_customer_autocomplete(select_first=False)
        except Exception:
            pass
        try:
            if self._results_list.count() > 0:
                item = self._results_list.item(0)
                if item:
                    self._results_list.setCurrentRow(0)
                    self._on_result_item_activated(item)
        except Exception:
            pass

    def _set_active(self, action: QAction) -> None:
        """Set the given action as active (checked) and uncheck others."""
        for act in (self.act_home, self.act_invoices):
            is_active = act is action
            act.setChecked(is_active)
            # swap icon to active/normal variant if available
            pair = self._icon_pairs.get(act)
            if pair:
                normal_icon, active_icon = pair
                act.setIcon(active_icon if is_active else normal_icon)

    @Slot()
    @Slot()
    def on_invoices_clicked(self):
        # switch to invoices placeholder view (index 1)
        self.stack.setCurrentIndex(1)
        self.status.setText("Showing Invoices")

    @Slot()
    def on_home_clicked(self):
        # switch to home page (index 0)
        self.stack.setCurrentIndex(0)
        self.status.setText("Home")


def main():
    # Avoid noisy Qt font-alias population messages by default; allow override via env var.
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts=false")

    app = QApplication(sys.argv)

    # Try to discover available styles for better debug/fallback logic.
    try:
        from PySide6.QtWidgets import QStyleFactory

        available = list(QStyleFactory.keys())
    except Exception:
        available = []

    # Respect CLI `-style` if provided (for example: `-style macOS`).
    requested_style = None
    for i, a in enumerate(sys.argv):
        if a == "-style" and i + 1 < len(sys.argv):
            requested_style = sys.argv[i + 1]
            break

    # If a style was explicitly requested, honor it when available,
    # otherwise fallback to 'macOS' if present, then 'Fusion'.
    if requested_style:
        if requested_style in available:
            app.setStyle(requested_style)
        else:
            fallback = "macOS" if "macOS" in available else "Fusion"
            if available:
                app.setStyle(fallback)
    else:
        # Default to macOS when available to match macOS Contacts look.
        if "macOS" in available:
            app.setStyle("macOS")
        else:
            pass

    # Determine the style class for potential fallback behavior.
    try:
        style_class = app.style().__class__.__name__
    except Exception:
        style_class = None

    # If the user requested 'macOS' but Qt fell back to QCommonStyle,
    # apply a gentle macOS-like palette so the app looks more native.
    try:
        if requested_style and requested_style.lower().startswith("mac") and style_class == "QCommonStyle":
            from PySide6.QtGui import QColor, QPalette

            mac_pal = QPalette()
            mac_pal.setColor(QPalette.ColorRole.Window, QColor("#ececec"))
            mac_pal.setColor(QPalette.ColorRole.Button, QColor("#ececec"))
            mac_pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            mac_pal.setColor(QPalette.ColorRole.Text, QColor("#000000"))
            mac_pal.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
            mac_pal.setColor(QPalette.ColorRole.Highlight, QColor("#a5cdff"))
            app.setPalette(mac_pal)
    except Exception:
        pass

    # Load a macOS-like QSS when requested or when we applied the macOS palette.
    try:
        qss_path = Path(__file__).parent / "assets" / "styles" / "macos.qss"
        if qss_path.exists() and (
            (requested_style and requested_style.lower().startswith("mac")) or style_class == "QCommonStyle"
        ):
            with qss_path.open("r", encoding="utf-8") as f:
                qss = f.read()
            if qss:
                app.setStyleSheet(qss)
    except Exception:
        pass

    app.setApplicationName("Sam Invoice")
    window = MainWindow()
    # Start maximized to give a larger initial workspace
    window.showMaximized()
    # Ensure Ctrl-C (SIGINT) in the terminal will terminate the app.
    try:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    except Exception:
        # If signals aren't available or setting fails, ignore.
        pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
