"""Sam Invoice main application."""

import os
import signal
import sys
from pathlib import Path

import qtawesome as qta
from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStyle,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from sam_invoice.models import database
from sam_invoice.ui.customer_view import CustomerView
from sam_invoice.ui.preferences_dialog import PreferencesDialog
from sam_invoice.ui.products_view import ProductsView


class MainWindow(QMainWindow):
    """Sam Invoice application main window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sam Invoice")
        self.setGeometry(100, 100, 800, 600)

        # Initialize settings
        self.settings = QSettings("SamInvoice", "SamInvoice")

        # Load last opened database or use default
        last_db = self.settings.value("last_database", None)
        if last_db and Path(last_db).exists():
            self.current_db_path = Path(last_db)
            database.set_database_path(self.current_db_path)
        else:
            self.current_db_path = database.DEFAULT_DB_PATH

        self._update_window_title()

        # === Menu Bar ===
        self._create_menu_bar()

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # === Toolbar ===
        toolbar = self._create_toolbar()
        self.addToolBar(toolbar)

        # === Stacked area for views ===
        self.stack = QStackedWidget()

        # Customers view (Home)
        self._customer_view = CustomerView()
        self.stack.addWidget(self._customer_view)

        # Products view
        self._products_view = ProductsView()
        self.stack.addWidget(self._products_view)

        # Invoices view (placeholder)
        invoices_placeholder = self._create_placeholder("Invoices (coming soon)")
        self.stack.addWidget(invoices_placeholder)

        main_layout.addWidget(self.stack)

        self.setCentralWidget(central_widget)

        # === Toolbar action connections ===
        self.act_home.triggered.connect(lambda: self._set_active(self.act_home) or self._show_view(0, "Customers"))
        self.act_articles.triggered.connect(
            lambda: self._set_active(self.act_articles) or self._show_view(1, "Products")
        )
        self.act_invoices.triggered.connect(
            lambda: self._set_active(self.act_invoices) or self._show_view(2, "Invoices")
        )

        # Activate Home by default
        self._set_active(self.act_home)

        # Restore window geometry and state
        self._restore_window_state()

    def _create_menu_bar(self):
        """Create the menu bar with File menu."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        # New database action
        new_action = QAction("&New Database...", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_database)
        file_menu.addAction(new_action)

        # Open database action
        open_action = QAction("&Open Database...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_database)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # Recent files menu
        self.recent_menu = file_menu.addMenu("Open &Recent")
        self._update_recent_files_menu()

        file_menu.addSeparator()

        # Quit action
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        # Preferences action
        prefs_action = QAction("&Preferences...", self)
        prefs_action.setShortcut("Ctrl+,")
        prefs_action.triggered.connect(self._open_preferences)
        edit_menu.addAction(prefs_action)

    def _create_toolbar(self) -> QToolBar:
        """Créer la barre d'outils avec les actions de navigation."""
        toolbar = QToolBar("Main")
        toolbar.setObjectName("MainToolbar")  # Set objectName for state saving
        toolbar.setMovable(False)

        # Unified toolbar on macOS
        if sys.platform == "darwin":
            self.setUnifiedTitleAndToolBarOnMac(True)

        # Dark gray color for all icons
        icon_color = "#444444"

        # Create icons with qtawesome
        home_icon = qta.icon("fa5s.users", color=icon_color)
        articles_icon = qta.icon("fa5s.wine-bottle", color=icon_color)
        invoices_icon = qta.icon("fa5s.file-invoice-dollar", color=icon_color)

        # Create actions
        self.act_home = QAction(home_icon, "Customers", self)
        self.act_home.setCheckable(True)
        self.act_articles = QAction(articles_icon, "Products", self)
        self.act_articles.setCheckable(True)
        self.act_invoices = QAction(invoices_icon, "Invoices", self)
        self.act_invoices.setCheckable(True)

        # Store icons (no need for colored variants)
        self._icon_pairs = {
            self.act_home: (home_icon, home_icon),
            self.act_articles: (articles_icon, articles_icon),
            self.act_invoices: (invoices_icon, invoices_icon),
        }

        # Add actions to toolbar
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.addAction(self.act_home)
        toolbar.addAction(self.act_articles)
        toolbar.addAction(self.act_invoices)

        return toolbar

    def _load_icon(self, path: Path, fallback: QStyle.StandardPixmap) -> QIcon:
        """Charger une icône depuis un fichier ou utiliser l'icône de fallback."""
        if path.exists():
            return QIcon(str(path))
        return self.style().standardIcon(fallback)

    def _colorize_icon(self, icon: QIcon, color: QColor) -> QIcon:
        """Créer une version colorée d'une icône."""
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

    def _create_placeholder(self, text: str) -> QWidget:
        """Créer un widget placeholder avec un texte centré."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        return widget

    def _set_active(self, action: QAction):
        """Set an action as active and deactivate others."""
        for act in (self.act_home, self.act_articles, self.act_invoices):
            is_active = act is action
            act.setChecked(is_active)

            # Change icon based on active/inactive state
            pair = self._icon_pairs.get(act)
            if pair:
                normal_icon, active_icon = pair
                act.setIcon(active_icon if is_active else normal_icon)

    def _show_view(self, index: int, label: str):
        """Display a specific view in the stack."""
        self.stack.setCurrentIndex(index)

    def _update_window_title(self):
        """Update window title with current database name."""
        db_name = self.current_db_path.name
        self.setWindowTitle(f"Sam Invoice - {db_name}")

    def _new_database(self):
        """Create a new database file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Create New Database", str(Path.home()), "SQLite Database (*.db);;All Files (*)"
        )

        if file_path:
            db_path = Path(file_path)
            # Ensure .db extension
            if not db_path.suffix:
                db_path = db_path.with_suffix(".db")

            # Remove file if it already exists
            if db_path.exists():
                reply = QMessageBox.question(
                    self,
                    "File Exists",
                    f"The file {db_path.name} already exists. Do you want to replace it?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return
                db_path.unlink()

            # Create new database
            database.set_database_path(db_path)
            database.init_db()

            self.current_db_path = db_path
            self._update_window_title()
            self._reload_views()
            self._add_to_recent_files(db_path)

            QMessageBox.information(self, "Database Created", f"New database created: {db_path.name}")

    def _open_database(self):
        """Open an existing database file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Database", str(Path.home()), "SQLite Database (*.db);;All Files (*)"
        )

        if file_path:
            db_path = Path(file_path)

            # Verify it's a valid SQLite database
            try:
                database.set_database_path(db_path)
                # Try to access the database
                with database.SessionLocal() as session:
                    # Quick check if tables exist
                    from sam_invoice.models.customer import Customer

                    session.query(Customer).first()

                self.current_db_path = db_path
                self._update_window_title()
                self._reload_views()
                self._add_to_recent_files(db_path)

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error Opening Database",
                    f"Failed to open database: {str(e)}\n\nPlease ensure it's a valid Sam Invoice database.",
                )

    def _reload_views(self):
        """Reload all views with new database."""
        # Reload customers view
        if hasattr(self._customer_view, "reload_items"):
            self._customer_view.reload_items()

        # Reload products view
        if hasattr(self._products_view, "reload_items"):
            self._products_view.reload_items()

    def _add_to_recent_files(self, db_path: Path):
        """Add a database file to recent files list."""
        # Save as last opened database
        self.settings.setValue("last_database", str(db_path.absolute()))

        # Get current recent files list
        recent_files = self.settings.value("recent_files", [])
        if not isinstance(recent_files, list):
            recent_files = []

        # Remove if already in list
        path_str = str(db_path.absolute())
        if path_str in recent_files:
            recent_files.remove(path_str)

        # Add to beginning of list
        recent_files.insert(0, path_str)

        # Keep only 5 most recent
        recent_files = recent_files[:5]

        # Save updated list
        self.settings.setValue("recent_files", recent_files)

        # Update menu
        self._update_recent_files_menu()

    def _update_recent_files_menu(self):
        """Update the recent files menu with current list."""
        self.recent_menu.clear()

        recent_files = self.settings.value("recent_files", [])
        if not isinstance(recent_files, list):
            recent_files = []

        if not recent_files:
            no_recent = QAction("No recent files", self)
            no_recent.setEnabled(False)
            self.recent_menu.addAction(no_recent)
            return

        for file_path in recent_files:
            path = Path(file_path)
            if path.exists():
                action = QAction(path.name, self)
                action.setToolTip(str(path))
                action.triggered.connect(lambda checked, p=path: self._open_recent_file(p))
                self.recent_menu.addAction(action)

        self.recent_menu.addSeparator()
        clear_action = QAction("Clear Recent Files", self)
        clear_action.triggered.connect(self._clear_recent_files)
        self.recent_menu.addAction(clear_action)

    def _open_recent_file(self, db_path: Path):
        """Open a database from recent files."""
        try:
            database.set_database_path(db_path)
            # Try to access the database
            with database.SessionLocal() as session:
                from sam_invoice.models.customer import Customer

                session.query(Customer).first()

            self.current_db_path = db_path
            self._update_window_title()
            self._reload_views()
            self._add_to_recent_files(db_path)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Opening Database",
                f"Failed to open database: {str(e)}\\n\\nPlease ensure it's a valid Sam Invoice database.",
            )
            # Remove from recent files if it failed
            recent_files = self.settings.value("recent_files", [])
            if isinstance(recent_files, list) and str(db_path) in recent_files:
                recent_files.remove(str(db_path))
                self.settings.setValue("recent_files", recent_files)
                self._update_recent_files_menu()

    def _clear_recent_files(self):
        """Clear the recent files list."""
        self.settings.setValue("recent_files", [])
        self._update_recent_files_menu()

    def _open_preferences(self):
        """Open preferences dialog."""
        dialog = PreferencesDialog(self)
        if dialog.exec():
            # Preferences saved successfully
            pass

    def _restore_window_state(self):
        """Restore window geometry and state from settings."""
        # Restore window geometry first
        geometry = self.settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default size if no saved geometry
            self.resize(1200, 800)

        # Restore window state (toolbars, dockwidgets, etc.)
        window_state = self.settings.value("window/state")
        if window_state:
            self.restoreState(window_state)

        # Check if was in fullscreen
        was_fullscreen = self.settings.value("window/fullscreen", False, type=bool)
        if was_fullscreen:
            self.showFullScreen()
        else:
            # Check if was maximized (only if not fullscreen)
            was_maximized = self.settings.value("window/maximized", False, type=bool)
            if was_maximized:
                self.showMaximized()

        # Restore splitter sizes for customer view
        customer_splitter_state = self.settings.value("splitters/customer_view")
        if customer_splitter_state and hasattr(self._customer_view, "_splitter"):
            self._customer_view._splitter.restoreState(customer_splitter_state)

        # Restore splitter sizes for products view
        products_splitter_state = self.settings.value("splitters/products_view")
        if products_splitter_state and hasattr(self._products_view, "_splitter"):
            self._products_view._splitter.restoreState(products_splitter_state)

    def _save_window_state(self):
        """Save window geometry and state to settings."""
        # Save window geometry
        self.settings.setValue("window/geometry", self.saveGeometry())

        # Save window state
        self.settings.setValue("window/state", self.saveState())

        # Save if window is fullscreen
        self.settings.setValue("window/fullscreen", self.isFullScreen())

        # Save if window is maximized (only relevant if not fullscreen)
        self.settings.setValue("window/maximized", self.isMaximized())

        # Save splitter states
        if hasattr(self._customer_view, "_splitter"):
            self.settings.setValue("splitters/customer_view", self._customer_view._splitter.saveState())

        if hasattr(self._products_view, "_splitter"):
            self.settings.setValue("splitters/products_view", self._products_view._splitter.saveState())

    def closeEvent(self, event):
        """Clean up resources before closing the application."""
        # Save window state
        self._save_window_state()

        # Clean up threads in views
        if hasattr(self, "_customer_view"):
            self._customer_view.cleanup()
        if hasattr(self, "_products_view"):
            # Add cleanup if ProductsView also has a thread
            if hasattr(self._products_view, "cleanup"):
                self._products_view.cleanup()
        super().closeEvent(event)


def main():
    """Main application entry point."""
    # Avoid verbose Qt messages
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts=false")

    # On macOS, set the process name before creating QApplication
    if sys.platform == "darwin":
        try:
            from Foundation import NSProcessInfo

            processInfo = NSProcessInfo.processInfo()
            processInfo.setProcessName_("Sam Invoice")
        except ImportError:
            # Foundation not available, try setting argv[0]
            if len(sys.argv) > 0:
                sys.argv[0] = "Sam Invoice"

    app = QApplication(sys.argv)

    # Set application name for macOS menu bar
    app.setApplicationName("Sam Invoice")
    app.setApplicationDisplayName("Sam Invoice")
    app.setOrganizationName("SamInvoice")
    app.setOrganizationDomain("sam-invoice.app")

    # Discover available styles
    try:
        from PySide6.QtWidgets import QStyleFactory

        available = list(QStyleFactory.keys())
    except Exception:
        available = []

    # Respect requested style from command line (-style macOS)
    requested_style = None
    for i, a in enumerate(sys.argv):
        if a == "-style" and i + 1 < len(sys.argv):
            requested_style = sys.argv[i + 1]
            break

    # Apply style
    if requested_style:
        if requested_style in available:
            app.setStyle(requested_style)
        else:
            fallback = "macOS" if "macOS" in available else "Fusion"
            if available:
                app.setStyle(fallback)
    else:
        # Default to macOS if available
        if "macOS" in available:
            app.setStyle("macOS")

    # Determine style class
    try:
        style_class = app.style().__class__.__name__
    except Exception:
        style_class = None

    # macOS palette if QCommonStyle
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

    # Load macOS QSS
    import platform

    try:
        # Determine base path for bundled app vs development
        if getattr(sys, "frozen", False):
            # Running in a PyInstaller bundle
            base_path = Path(sys._MEIPASS)
        else:
            # Running in normal Python environment
            base_path = Path(__file__).parent

        qss_path = base_path / "sam_invoice" / "assets" / "styles" / "macos.qss"
        if not qss_path.exists():
            # Try alternative path for development
            qss_path = base_path / "assets" / "styles" / "macos.qss"

        # Apply macOS style if on macOS platform or if explicitly requested
        should_apply_macos_style = (
            platform.system() == "Darwin"  # Always on macOS
            or (requested_style and requested_style.lower().startswith("mac"))
            or style_class == "QCommonStyle"
        )
        if qss_path.exists() and should_apply_macos_style:
            with qss_path.open("r", encoding="utf-8") as f:
                qss = f.read()
            if qss:
                app.setStyleSheet(qss)
    except Exception as e:
        print(f"Warning: Could not load QSS: {e}")

    app.setApplicationName("Sam Invoice")

    # Créer la fenêtre
    window = MainWindow()
    window.show()  # Let the window restore its own state

    # Configurer la gestion de Ctrl-C pour fermer proprement
    def sigint_handler(signum, frame):
        """Handler pour Ctrl-C qui ferme proprement l'application."""
        print("\nFermeture de l'application...")
        QApplication.quit()

    signal.signal(signal.SIGINT, sigint_handler)

    # Timer pour permettre à Python de traiter les signaux pendant la boucle Qt
    from PySide6.QtCore import QTimer

    timer = QTimer()
    timer.timeout.connect(lambda: None)  # Juste pour réveiller la boucle d'événements
    timer.start(500)  # Toutes les 500ms

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
