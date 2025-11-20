import sys

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sam_invoice.ui.customers_view import CustomersView


class MainWindow(QMainWindow):
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

        # Buttons area (header)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)

        self.customers_btn = QPushButton("Customers")
        self.customers_btn.setObjectName("customers_btn")
        self.customers_btn.setFixedSize(140, 40)

        self.invoices_btn = QPushButton("Invoices")
        self.invoices_btn.setObjectName("invoices_btn")
        self.invoices_btn.setFixedSize(140, 40)

        btn_layout.addStretch()
        btn_layout.addWidget(self.customers_btn)
        btn_layout.addWidget(self.invoices_btn)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # Stacked area for views
        self.stack = QStackedWidget()
        # customers view (embedded)
        self.customers_view = CustomersView(parent=self)
        # invoices placeholder
        invoices_placeholder = QWidget()
        ph_layout = QVBoxLayout(invoices_placeholder)
        ph_label = QLabel("Invoices view (coming soon)")
        ph_label.setAlignment(Qt.AlignCenter)
        ph_layout.addWidget(ph_label)

        self.stack.addWidget(self.customers_view)
        self.stack.addWidget(invoices_placeholder)

        main_layout.addWidget(self.stack)

        # status label
        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status)

        self.setCentralWidget(central_widget)

        # Connect signals
        self.customers_btn.clicked.connect(self.on_customers_clicked)
        self.invoices_btn.clicked.connect(self.on_invoices_clicked)

    @Slot()
    def on_customers_clicked(self):
        # Placeholder action — will be connected to actual view later
        # switch to customers view in the stacked widget
        self.stack.setCurrentIndex(0)
        self.status.setText("Showing Customers")

    @Slot()
    def on_invoices_clicked(self):
        # switch to invoices placeholder view
        self.stack.setCurrentIndex(1)
        self.status.setText("Showing Invoices")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Sam Invoice")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
