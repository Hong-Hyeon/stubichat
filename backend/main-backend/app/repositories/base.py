from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from uuid import UUID

from app.core.database import Base

T = TypeVar('T', bound=Base)


class BaseRepository(ABC, Generic[T]):
    """Base repository interface for database operations."""
    
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model
    
    @abstractmethod
    async def create(self, **kwargs) -> T:
        """Create a new entity."""
        pass
    
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[T]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    async def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]:
        """Get all entities with optional pagination."""
        pass
    
    @abstractmethod
    async def update(self, id: UUID, **kwargs) -> Optional[T]:
        """Update entity by ID."""
        pass
    
    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete entity by ID."""
        pass
    
    @abstractmethod
    async def exists(self, id: UUID) -> bool:
        """Check if entity exists by ID."""
        pass


class SQLAlchemyRepository(BaseRepository[T]):
    """SQLAlchemy implementation of the base repository."""
    
    async def create(self, **kwargs) -> T:
        """Create a new entity."""
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def get_by_id(self, id: UUID) -> Optional[T]:
        """Get entity by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]:
        """Get all entities with optional pagination."""
        query = select(self.model)
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update(self, id: UUID, **kwargs) -> Optional[T]:
        """Update entity by ID."""
        result = await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        await self.session.commit()
        return result.scalar_one_or_none()
    
    async def delete(self, id: UUID) -> bool:
        """Delete entity by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def exists(self, id: UUID) -> bool:
        """Check if entity exists by ID."""
        result = await self.session.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None 