"""
Generic BaseRepository[T] — Liskov Substitution Principle.
All concrete repositories substitute this without breaking callers.
Services depend on this abstraction (Dependency Inversion Principle).
"""
from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from ..database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic CRUD repository.
    Subclasses inherit create/get/list/update/delete and add domain-specific queries.
    """

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: int) -> Optional[ModelType]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def count(self) -> int:
        return self.db.query(self.model).count()

    def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, id: int) -> bool:
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True
        return False

    def bulk_create(self, objects: List[ModelType]) -> List[ModelType]:
        self.db.bulk_save_objects(objects)
        self.db.commit()
        return objects
