"""Customer view using the base class."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMessageBox

from sam_invoice.models.crud_customer import customer_crud
from sam_invoice.ui.base_widgets import BaseListView
from sam_invoice.ui.customer_detail import CustomerDetailWidget


class CustomerView(BaseListView):
    """Customer view widget with two-column layout.

    Left column: search and customer list
    Right column: customer detail with edit/save/delete actions
    """

    customer_selected = Signal(object)

    def _search_placeholder(self) -> str:
        """Search placeholder text."""
        return "Search for a customer (name, email)..."

    def _search_function(self, query: str, limit: int):
        """Search function for customers."""
        rows = customer_crud.search(query, limit=limit)
        return sorted(rows, key=lambda c: (getattr(c, "name", "") or "").lower())

    def _create_detail_widget(self):
        """Create the customer detail widget."""
        detail = CustomerDetailWidget(self)
        # Signals are already connected in BaseListView.__init__
        return detail

    def _get_all_items(self):
        """Get all customers."""
        return customer_crud.get_all()

    def _format_list_item(self, customer) -> str:
        """Format a customer for display in the list."""
        name = getattr(customer, "name", "") or "(no name)"
        email = getattr(customer, "email", "")
        if email:
            return f"{name} ({email})"
        return name

    def _on_saved(self, data: dict):
        """Callback when a customer is saved."""
        cust_id = data.get("id")
        try:
            if cust_id:
                # Update
                customer_crud.update(
                    cust_id, name=data.get("name"), address=data.get("address"), email=data.get("email")
                )
            else:
                # Create
                customer_crud.create(name=data.get("name"), address=data.get("address"), email=data.get("email"))
            self.reload_items()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save customer: {e}")

    def _on_deleted(self, cust_id: int):
        """Callback when a customer is deleted."""
        try:
            customer_crud.delete(cust_id)
            self.reload_items()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete customer: {e}")

    def _on_item_activated(self, item):
        """Callback when an item is activated."""
        if not item:
            return
        selected_customer = item.data(Qt.ItemDataRole.UserRole)
        self._detail_widget.set_customer(selected_customer)
        self.customer_selected.emit(selected_customer)

    def _on_add_item(self):
        """Callback to add a new item."""
        # Clear selection
        self._results_list.clearSelection()
        self._detail_widget.set_customer(None)
        # Enter edit mode
        self._detail_widget._enter_edit_mode(True)
