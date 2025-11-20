from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import sam_invoice.models.crud_customer as crud


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
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        btn_layout.addStretch()
        btn_layout.addWidget(self.refresh_btn)
        layout.addLayout(btn_layout)

        self.refresh_btn.clicked.connect(self.refresh)
        # filter on text change (reactive)
        self.search.textChanged.connect(self._apply_filter)

        # internal cache of customers (list of ORM objects)
        self._customers = []

        # initial load
        self.refresh()

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

        for r, c in enumerate(rows):
            self.table.insertRow(r)
            id_item = QTableWidgetItem(str(getattr(c, "id", "")))
            name_item = QTableWidgetItem(getattr(c, "name", ""))
            addr_item = QTableWidgetItem(getattr(c, "address", ""))
            email_item = QTableWidgetItem(getattr(c, "email", ""))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 0, id_item)
            self.table.setItem(r, 1, name_item)
            self.table.setItem(r, 2, addr_item)
            self.table.setItem(r, 3, email_item)
