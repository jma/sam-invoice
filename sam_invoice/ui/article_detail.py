"""Article detail widget using the base class."""

from PySide6.QtWidgets import QMessageBox

from sam_invoice.ui.base_widgets import BaseDetailWidget


class ArticleDetailWidget(BaseDetailWidget):
    """Article detail widget with view/edit mode.

    Displays article information (reference, name, price, stock, sold)
    with the ability to edit, save and delete.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Define signal aliases
        self.article_saved = self.item_saved
        self.article_deleted = self.item_deleted

        # Store raw values for editing
        self._raw_values = {}

        # Add article-specific fields
        self._add_field("reference", "", "e.g. ART-001", is_primary=True)
        self._add_field("name", "", "Product name", word_wrap=True)
        self._add_field("price", "", "Price (e.g. 12.50)")
        self._add_field("stock", "", "Stock (integer)")
        self._add_field("sold", "", "Sold (integer)")

        # Finalize layout
        self._finalize_layout()

        # Load icon
        self._load_avatar_icon("articles")

    def _save_changes(self):
        """Save article changes."""
        data = {
            "id": self._current_id,
            "reference": self._fields["reference"][1].text().strip(),
            "name": self._fields["name"][1].text().strip(),
            "price": self._to_float(self._fields["price"][1].text()),
            "stock": self._to_int(self._fields["stock"][1].text()),
            "sold": self._to_int(self._fields["sold"][1].text()),
        }
        self.article_saved.emit(data)
        self._enter_edit_mode(False)

    def _on_delete_clicked(self):
        """Ask for confirmation and delete the article."""
        if self._current_id is None:
            return

        reference = self._fields["reference"][0].text() or ""
        res = QMessageBox.question(
            self,
            "Delete",
            f"Delete article '{reference}'? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if res == QMessageBox.StandardButton.Yes:
            self.article_deleted.emit(int(self._current_id))

    def _validate_fields(self) -> bool:
        """Validate form fields."""
        reference = self._fields["reference"][1].text().strip()
        name = self._fields["name"][1].text().strip()
        price_str = self._fields["price"][1].text().strip()

        valid = True  # Reference validation
        reference_label, reference_edit, reference_err = self._fields["reference"]
        if not reference:
            reference_err.setText("Reference is required")
            reference_err.setVisible(True)
            valid = False
        else:
            reference_err.setVisible(False)

        # Name validation
        name_label, name_edit, name_err = self._fields["name"]
        if not name:
            name_err.setText("Name is required")
            name_err.setVisible(True)
            valid = False
        else:
            name_err.setVisible(False)

        # Price validation
        price_label, price_edit, price_err = self._fields["price"]
        price = self._to_float(price_str)
        if price is None:
            price_err.setText("Invalid price (use decimal number)")
            price_err.setVisible(True)
            valid = False
        else:
            price_err.setVisible(False)

        # Stock validation (optional, no visible error)

        # Sold validation (optional, no visible error)

        self._save_btn.setEnabled(valid)
        return valid

    def set_article(self, art):
        """Display article information."""
        self._current_id = getattr(art, "id", None) if art else None

        if not art:
            # Clear display
            self._fields["reference"][0].setText("")
            self._fields["name"][0].setText("")
            self._fields["price"][0].setText("")
            self._fields["stock"][0].setText("")
            self._fields["sold"][0].setText("")
            self._raw_values = {}
            self._edit_btn.setEnabled(False)
            self._edit_btn.setVisible(False)
            self._delete_btn.setEnabled(False)
        else:
            # Store raw values
            self._raw_values = {
                "reference": getattr(art, "reference", ""),
                "name": getattr(art, "name", ""),
                "price": str(getattr(art, "price", 0.0)),
                "stock": str(getattr(art, "stock", 0)),
                "sold": str(getattr(art, "sold", 0)),
            }

            # Display article data with formatting
            self._fields["reference"][0].setText(self._raw_values["reference"])
            self._fields["name"][0].setText(self._raw_values["name"])

            # Formatted price
            price = getattr(art, "price", 0.0)
            self._fields["price"][0].setText(f"Price: {price:.2f} €" if price else "")

            # Stock and sold
            stock = getattr(art, "stock", 0)
            self._fields["stock"][0].setText(f"Stock: {stock}")

            sold = getattr(art, "sold", 0)
            self._fields["sold"][0].setText(f"Sold: {sold}")

            self._edit_btn.setEnabled(True)
            self._edit_btn.setVisible(True)
            self._delete_btn.setEnabled(self._current_id is not None)

    def _enter_edit_mode(self, editing: bool):
        """Toggle between view and edit mode."""
        self.editing_changed.emit(editing)

        # Show/hide widgets
        for field_name, (label, edit, _error) in self._fields.items():
            label.setVisible(not editing)
            edit.setVisible(editing)
            if editing:
                # Use raw values instead of formatted label text
                raw_value = self._raw_values.get(field_name, "")
                edit.setText(raw_value)

        self._edit_btn.setVisible(not editing)
        self._save_btn.setVisible(editing)
        self._cancel_btn.setVisible(editing)
        self._delete_btn.setVisible(not editing and self._current_id is not None)

        if editing:
            self._validate_fields()

    # === Utility methods for conversion ===

    @staticmethod
    def _to_float(s: str):
        """Convert a string to float, return None if invalid."""
        try:
            return float(s) if s.strip() else 0.0
        except ValueError:
            return None

    @staticmethod
    def _to_int(s: str) -> int:
        """Convert a string to int, return 0 if empty or invalid."""
        try:
            return int(s) if s.strip() else 0
        except ValueError:
            return 0
