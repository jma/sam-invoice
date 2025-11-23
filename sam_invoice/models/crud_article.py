"""CRUD operations for articles."""

from sqlalchemy import func

from . import database
from .article import Article


def create_article(
    reference: str, name: str = None, price: float | None = None, stock: int | None = None, sold: int | None = None
):
    """Create a new article in the database."""
    session = database.SessionLocal()
    try:
        art = Article(reference=reference, name=name, price=price, stock=stock, sold=sold)
        session.add(art)
        session.commit()
        session.refresh(art)
        return art
    finally:
        session.close()


def get_articles():
    """Retrieve all articles, sorted by reference."""
    session = database.SessionLocal()
    try:
        return session.query(Article).order_by(func.lower(Article.reference)).all()
    finally:
        session.close()


def search_articles(query: str, limit: int | None = None):
    """Search for articles by exact ID or partial match on reference/name.

    Args:
        query: Search text
        limit: Maximum number of results (None = no limit)

    Returns:
        List of matching Article objects
    """
    session = database.SessionLocal()
    try:
        q = (query or "").strip()

        # If no search query, return all articles
        if not q:
            stmt = session.query(Article).order_by(func.lower(Article.reference))
            return stmt.limit(limit).all() if limit else stmt.all()

        # Build search filters
        filters = [
            Article.reference.ilike(f"%{q}%"),
            Article.name.ilike(f"%{q}%"),
        ]

        # Add ID filter if search is numeric
        try:
            filters.append(Article.id == int(q))
        except ValueError:
            pass

        # Execute search
        from sqlalchemy import or_

        stmt = session.query(Article).filter(or_(*filters)).order_by(func.lower(Article.reference))
        return stmt.limit(limit).all() if limit else stmt.all()
    finally:
        session.close()


def get_article_by_id(article_id: int):
    """Retrieve an article by its ID."""
    session = database.SessionLocal()
    try:
        return session.query(Article).filter(Article.id == article_id).first()
    finally:
        session.close()


def update_article(
    article_id: int, reference: str = None, name: str = None, price: float = None, stock: int = None, sold: int = None
):
    """Update information for an existing article."""
    session = database.SessionLocal()
    try:
        art = session.query(Article).filter(Article.id == article_id).first()
        if art:
            if reference is not None:
                art.reference = reference
            if name is not None:
                art.name = name
            if price is not None:
                art.price = price
            if stock is not None:
                art.stock = stock
            if sold is not None:
                art.sold = sold
            session.commit()
            session.refresh(art)
        return art
    finally:
        session.close()


def delete_article(article_id: int):
    """Delete an article from the database."""
    session = database.SessionLocal()
    try:
        art = session.query(Article).filter(Article.id == article_id).first()
        if art:
            session.delete(art)
            session.commit()
        return art
    finally:
        session.close()
