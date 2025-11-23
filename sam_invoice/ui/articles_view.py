"""Articles view using the base class."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMessageBox

import sam_invoice.models.crud_article as crud
from sam_invoice.ui.article_detail import ArticleDetailWidget
from sam_invoice.ui.base_widgets import BaseListView


class ArticlesView(BaseListView):
    """Articles view widget with two-column layout.

    Left column: search and article list
    Right column: article details with edit/save/delete actions
    """

    article_selected = Signal(object)

    def _search_placeholder(self) -> str:
        """Search placeholder text."""
        return "Search articles (reference, name)..."

    def _search_function(self, query: str, limit: int):
        """Search function for articles."""
        rows = crud.search_articles(query, limit=limit)
        return sorted(rows, key=lambda a: (getattr(a, "reference", "") or "").lower())

    def _create_detail_widget(self):
        """Create article detail widget."""
        detail = ArticleDetailWidget(self)
        detail.article_saved.connect(self._on_saved)
        detail.article_deleted.connect(self._on_deleted)
        return detail

    def _get_all_items(self):
        """Get all articles."""
        return crud.get_articles()

    def _format_list_item(self, article) -> str:
        """Format an article for display in the list."""
        reference = getattr(article, "reference", "") or "(no reference)"
        name = getattr(article, "name", "")
        if name:
            return f"{reference} - {name}"
        return reference

    def _on_saved(self, data: dict):
        """Callback when an article is saved."""
        art_id = data.get("id")
        try:
            if art_id:
                # Update
                crud.update_article(
                    art_id,
                    reference=data.get("reference"),
                    name=data.get("name"),
                    price=data.get("price"),
                    stock=data.get("stock"),
                    sold=data.get("sold"),
                )
            else:
                # Create
                crud.create_article(
                    reference=data.get("reference"),
                    name=data.get("name"),
                    price=data.get("price"),
                    stock=data.get("stock"),
                    sold=data.get("sold"),
                )
            self.reload_items()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save article: {e}")

    def _on_deleted(self, art_id: int):
        """Callback when an article is deleted."""
        try:
            crud.delete_article(art_id)
            self.reload_items()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete article: {e}")

    def _on_item_activated(self, item):
        """Callback when an item is activated."""
        if not item:
            return
        selected_article = item.data(Qt.ItemDataRole.UserRole)
        self._detail_widget.set_article(selected_article)
        self.article_selected.emit(selected_article)

    def _on_add_item(self):
        """Callback to add a new item."""
        # Clear selection
        self._results_list.clearSelection()
        self._detail_widget.set_article(None)
        # Enter edit mode
        self._detail_widget._enter_edit_mode(True)
