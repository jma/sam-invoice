from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import sam_invoice.models.crud_customer as crud


class NumericTableWidgetItem(QTableWidgetItem):
    """Table item that sorts by an integer stored in Qt.UserRole when possible."""

    def __lt__(self, other: "NumericTableWidgetItem") -> bool:  # type: ignore[override]
        try:
            a = int(self.data(Qt.UserRole))
            b = int(other.data(Qt.UserRole))
            return a < b
        except Exception:
            return super().__lt__(other)


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


class CustomersView(QWidget):
    """Customers view showing a table (ID, Name, Address, Email) with a Refresh button.

    Uses `crud.get_customers()` to load rows.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Customers")
        layout = QVBoxLayout(self)

        header = QLabel("Customers")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size:14pt; font-weight:600; padding:6px;")
        layout.addWidget(header)

        # Search box
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher par nom, email, adresse ou ID…")
        layout.addWidget(self.search)

        # Table widget
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Address", "Email"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # enable interactive sorting by clicking headers
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.delete_btn = QPushButton("Delete")
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.refresh_btn = QPushButton("Refresh")
        btn_layout.addStretch()
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.refresh_btn)
        layout.addLayout(btn_layout)

        self.refresh_btn.clicked.connect(self.refresh)
        # filter on text change (reactive)
        self.search.textChanged.connect(self._apply_filter)
        # add / edit handlers
        self.add_btn.clicked.connect(self.on_add)
        self.delete_btn.clicked.connect(self.on_delete)
        self.edit_btn.clicked.connect(self.on_edit)

        # enable edit button only when a row is selected
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        # open editor on double click
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        # internal cache of customers (list of ORM objects)
        self._customers = []

        # initial load
        self.refresh()
        # default sort by Name (column 1) ascending on first load
        try:
            self.table.sortItems(1, Qt.AscendingOrder)
        except Exception:
            pass

    def refresh(self):
        """Reload customers from DB and populate the table."""
        self.table.setRowCount(0)
        try:
            customers = crud.get_customers()
        except Exception:
            # If DB isn't available or other error, show a single-row error
            self.table.setRowCount(1)
            self.table.setSpan(0, 0, 1, 4)
            item = QTableWidgetItem("Error loading customers")
            self.table.setItem(0, 0, item)
            return

        # Cache full list then apply filter to populate view
        self._customers = list(customers)
        self._apply_filter()

    def _apply_filter(self, text: str | None = None):
        """Filter cached customers and populate the table.

        Matches ID, name, address or email case-insensitively.
        """
        query = (text if text is not None else self.search.text()).strip().lower()
        self.table.setRowCount(0)

        if not self._customers:
            return

        # If there's a query, prefer server-side search via CRUD
        if query:
            try:
                rows = crud.search_customers(query)
            except Exception:
                rows = [
                    c
                    for c in self._customers
                    if query
                    in " ".join(
                        [
                            str(getattr(c, "id", "")),
                            getattr(c, "name", ""),
                            getattr(c, "address", ""),
                            getattr(c, "email", ""),
                        ]
                    ).lower()
                ]
        else:
            rows = list(self._customers)

        # disable sorting while populating to avoid items shifting
        was_sorting = self.table.isSortingEnabled()
        if was_sorting:
            self.table.setSortingEnabled(False)

        for r, c in enumerate(rows):
            self.table.insertRow(r)
            raw_id = getattr(c, "id", None)
            id_item = NumericTableWidgetItem(str(raw_id) if raw_id is not None else "")
            try:
                id_item.setData(Qt.UserRole, int(raw_id) if raw_id is not None else 0)
            except Exception:
                id_item.setData(Qt.UserRole, 0)
            name_item = QTableWidgetItem(getattr(c, "name", ""))
            addr_item = QTableWidgetItem(getattr(c, "address", ""))
            email_item = QTableWidgetItem(getattr(c, "email", ""))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 0, id_item)
            self.table.setItem(r, 1, name_item)
            self.table.setItem(r, 2, addr_item)
            self.table.setItem(r, 3, email_item)
        # restore sorting state
        if was_sorting:
            self.table.setSortingEnabled(True)

    def _on_selection_changed(self, selected, deselected):
        # enable edit if there is any selected row
        has = self.table.selectionModel().hasSelection()
        self.edit_btn.setEnabled(bool(has))
        self.delete_btn.setEnabled(bool(has))

    def _get_selected_customer_id(self) -> int | None:
        sels = self.table.selectionModel().selectedRows()
        if not sels:
            return None
        row = sels[0].row()
        item = self.table.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except Exception:
            return None

    def _on_cell_double_clicked(self, row: int, column: int):
        # ensure the clicked row becomes selected, then open editor
        try:
            self.table.selectRow(row)
        except Exception:
            pass
        self.on_edit()

    def on_add(self):
        dlg = CustomerDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.values()
            try:
                crud.create_customer(data["name"], data["address"], data["email"])  # type: ignore[arg-type]
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create customer: {e}")
            else:
                self.refresh()

    def on_edit(self):
        cid = self._get_selected_customer_id()
        if cid is None:
            QMessageBox.information(self, "Edit customer", "Please select a customer to edit.")
            return
        # fetch current values
        cust = None
        try:
            cust = crud.get_customer_by_id(cid)
        except Exception:
            cust = None

        if not cust:
            QMessageBox.warning(self, "Edit customer", "Selected customer not found.")
            self.refresh()
            return

        dlg = CustomerDialog(parent=self, name=cust.name, address=cust.address, email=cust.email)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.values()
            try:
                crud.update_customer(cid, name=data["name"], address=data["address"], email=data["email"])
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update customer: {e}")
            else:
                self.refresh()

    def on_delete(self):
        cid = self._get_selected_customer_id()
        if cid is None:
            QMessageBox.information(self, "Delete customer", "Please select a customer to delete.")
            return
        # confirm deletion
        res = QMessageBox.question(
            self,
            "Delete",
            f"Delete customer #{cid}? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return
        try:
            crud.delete_customer(cid)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete customer: {e}")
            return
        # refresh table after deletion
        self.refresh()


class CustomerDialog(QDialog):
    """Simple dialog to create or edit a customer."""

    def __init__(self, parent=None, name: str = "", address: str = "", email: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Customer")
        self.setModal(True)
        # make dialog slightly larger for comfortable editing
        self.resize(480, 220)

        self._name = QLineEdit(name)
        self._address = QLineEdit(address)
        self._email = QLineEdit(email)

        # placeholders to guide the user
        try:
            self._name.setPlaceholderText("e.g. John Doe")
            self._address.setPlaceholderText("e.g. 1 Wine St, Apt 2")
            self._email.setPlaceholderText("e.g. name@example.com")
        except Exception:
            pass

        # validation labels shown under each input
        self._name_err = QLabel("")
        self._address_err = QLabel("")
        self._name_err.setStyleSheet("color: #c00; font-size:11px;")
        self._address_err.setStyleSheet("color: #c00; font-size:11px;")
        self._name_err.setVisible(False)
        self._address_err.setVisible(False)
        # Use a vertical layout so we can pin the buttons to the bottom
        main_layout = QVBoxLayout(self)

        form = QFormLayout()
        # mark required fields with '*'
        form.addRow("Name *:", self._name)
        form.addRow("", self._name_err)
        form.addRow("Address *:", self._address)
        form.addRow("", self._address_err)
        form.addRow("Email:", self._email)

        main_layout.addLayout(form)
        # stretch to push buttons to the bottom
        main_layout.addStretch()

        btns = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self._on_ok)
        cancel.clicked.connect(self.reject)
        # OK disabled until form valid
        ok.setEnabled(False)
        self._ok_button = ok

        # reactive validation while typing
        self._name.textChanged.connect(self._on_field_changed)
        self._address.textChanged.connect(self._on_field_changed)
        self._email.textChanged.connect(self._on_field_changed)

        btns.addStretch()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        main_layout.addLayout(btns)

    def values(self) -> dict:
        return {
            "name": self._name.text().strip(),
            "address": self._address.text().strip(),
            "email": self._email.text().strip(),
        }

    def _on_ok(self):
        data = self.values()
        valid, msg = validate_customer_fields(data.get("name", ""), data.get("address", ""))
        if not valid:
            QMessageBox.warning(self, "Validation", msg or "Invalid data")
            return
        self.accept()

    def _on_field_changed(self, *_args):
        """Validate individual fields and enable/disable OK button."""
        name = self._name.text().strip()
        address = self._address.text().strip()
        # name validation
        if not name:
            self._name_err.setText("Name is required")
            self._name_err.setVisible(True)
        else:
            self._name_err.setVisible(False)

        # address validation
        if not address:
            self._address_err.setText("Address is required")
            self._address_err.setVisible(True)
        else:
            self._address_err.setVisible(False)

        # overall validity
        valid, _ = validate_customer_fields(name, address)
        self._ok_button.setEnabled(valid)
