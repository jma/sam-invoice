"""Base CRUD class for all entities."""

from abc import ABC, abstractmethod
from typing import TypeVar

from sqlalchemy import or_

from .database import SessionLocal

T = TypeVar("T")


class BaseCRUD[T](ABC):
    """Abstract base class for CRUD operations.

    Provides generic implementations for common operations and
    requires subclasses to implement entity-specific logic.
    """

    def __init__(self, model_class: type[T]):
        """Initialize with the SQLAlchemy model class.

        Args:
            model_class: The SQLAlchemy model class to perform CRUD on
        """
        self.model = model_class

    def get_all(self) -> list[T]:
        """Retrieve all entities, sorted by the default field.

        Returns:
            List of all entities
        """
        with SessionLocal() as session:
            return session.query(self.model).order_by(self._get_sort_field()).all()

    def get_by_id(self, entity_id: int) -> T | None:
        """Retrieve an entity by its ID.

        Args:
            entity_id: The entity's ID

        Returns:
            The entity if found, None otherwise
        """
        with SessionLocal() as session:
            return session.query(self.model).filter(self.model.id == entity_id).first()

    def delete(self, entity_id: int) -> T | None:
        """Delete an entity from the database.

        Args:
            entity_id: The entity's ID

        Returns:
            The deleted entity if found, None otherwise
        """
        with SessionLocal() as session:
            entity = session.query(self.model).filter(self.model.id == entity_id).first()
            if entity:
                session.delete(entity)
                session.commit()
            return entity

    def search(self, query: str, limit: int | None = None) -> list[T]:
        """Search for entities matching the query.

        Args:
            query: Search text
            limit: Maximum number of results (None = no limit)

        Returns:
            List of matching entities
        """
        with SessionLocal() as session:
            q = (query or "").strip()

            # If no search query, return all
            if not q:
                stmt = session.query(self.model).order_by(self._get_sort_field())
                return stmt.limit(limit).all() if limit else stmt.all()

            # Build search filters
            filters = self._get_search_filters(q)

            # Add ID filter if search is numeric
            try:
                filters.append(self.model.id == int(q))
            except ValueError:
                pass

            # Execute search
            stmt = session.query(self.model).filter(or_(*filters)).order_by(self._get_sort_field())
            return stmt.limit(limit).all() if limit else stmt.all()

    @abstractmethod
    def create(self, **kwargs) -> T:
        """Create a new entity.

        Args:
            **kwargs: Entity-specific fields

        Returns:
            The created entity
        """
        pass

    @abstractmethod
    def update(self, entity_id: int, **kwargs) -> T | None:
        """Update an existing entity.

        Args:
            entity_id: The entity's ID
            **kwargs: Fields to update

        Returns:
            The updated entity if found, None otherwise
        """
        pass

    @abstractmethod
    def _get_search_filters(self, query: str) -> list:
        """Get entity-specific search filters.

        Args:
            query: Search text

        Returns:
            List of SQLAlchemy filter expressions
        """
        pass

    @abstractmethod
    def _get_sort_field(self):
        """Get the field to sort by.

        Returns:
            SQLAlchemy column expression for sorting
        """
        pass
