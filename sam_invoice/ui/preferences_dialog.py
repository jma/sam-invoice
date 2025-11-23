"""Preferences dialog for company information."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from sam_invoice.models import crud_company


class PreferencesDialog(QDialog):
    """Dialog for editing company information and logo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences - Company Information")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        # Store logo data
        self.logo_data = None

        # Main layout
        layout = QVBoxLayout(self)

        # Company name
        name_label = QLabel("Company Name:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter company name")
        layout.addWidget(name_label)
        layout.addWidget(self.name_edit)

        # Address
        address_label = QLabel("Address:")
        self.address_edit = QTextEdit()
        self.address_edit.setPlaceholderText("Enter company address")
        self.address_edit.setMaximumHeight(80)
        layout.addWidget(address_label)
        layout.addWidget(self.address_edit)

        # Email
        email_label = QLabel("Email:")
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("contact@company.com")
        layout.addWidget(email_label)
        layout.addWidget(self.email_edit)

        # Phone
        phone_label = QLabel("Phone:")
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+1 234 567 8900")
        layout.addWidget(phone_label)
        layout.addWidget(self.phone_edit)

        # Logo section
        logo_label = QLabel("Company Logo:")
        layout.addWidget(logo_label)

        logo_layout = QHBoxLayout()
        self.logo_display = QLabel()
        self.logo_display.setFixedSize(150, 150)
        self.logo_display.setAlignment(Qt.AlignCenter)
        self.logo_display.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        self.logo_display.setText("No logo")
        logo_layout.addWidget(self.logo_display)

        logo_buttons_layout = QVBoxLayout()
        self.load_logo_btn = QPushButton("Load Logo...")
        self.load_logo_btn.clicked.connect(self._load_logo)
        self.clear_logo_btn = QPushButton("Clear Logo")
        self.clear_logo_btn.clicked.connect(self._clear_logo)
        logo_buttons_layout.addWidget(self.load_logo_btn)
        logo_buttons_layout.addWidget(self.clear_logo_btn)
        logo_buttons_layout.addStretch()

        logo_layout.addLayout(logo_buttons_layout)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)

        layout.addStretch()

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        save_btn.setDefault(True)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

        # Load existing data
        self._load_company_data()

    def _load_company_data(self):
        """Load existing company data from database."""
        company = crud_company.get_company()
        if company:
            self.name_edit.setText(company.name or "")
            self.address_edit.setText(company.address or "")
            self.email_edit.setText(company.email or "")
            self.phone_edit.setText(company.phone or "")

            if company.logo:
                self.logo_data = company.logo
                self._display_logo(self.logo_data)

    def _load_logo(self):
        """Load logo from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Company Logo", str(Path.home()), "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "rb") as f:
                    self.logo_data = f.read()
                self._display_logo(self.logo_data)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load logo: {e}")

    def _display_logo(self, logo_data: bytes):
        """Display logo in preview."""
        if logo_data:
            pixmap = QPixmap()
            pixmap.loadFromData(logo_data)
            if not pixmap.isNull():
                scaled = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_display.setPixmap(scaled)
                self.logo_display.setText("")

    def _clear_logo(self):
        """Clear logo."""
        self.logo_data = None
        self.logo_display.clear()
        self.logo_display.setText("No logo")

    def _save(self):
        """Save company information."""
        name = self.name_edit.text().strip()
        address = self.address_edit.toPlainText().strip()
        email = self.email_edit.text().strip()
        phone = self.phone_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "Validation Error", "Company name is required.")
            return

        try:
            crud_company.create_or_update_company(
                name=name, address=address, email=email, phone=phone, logo=self.logo_data
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save company information: {e}")
