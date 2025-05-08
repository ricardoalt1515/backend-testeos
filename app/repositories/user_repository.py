from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.db.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.database_schemas import UserCreate, UserUpdate

logger = logging.getLogger("hydrous")


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Obtener un usuario por su email"""
        try:
            return db.query(User).filter(User.email == email).first()
        except SQLAlchemyError as e:
            logger.error(f"Error en get_by_email: {e}")
            return None

    def create_with_hashed_password(
        self, db: Session, *, obj_in: UserCreate, hashed_password: str
    ) -> Optional[User]:
        """Crear un usuario con contraseña hasheada"""
        try:
            # Crear diccionario con los datos
            user_data = {}
            if hasattr(obj_in, "dict"):
                # Si es un objeto Pydantic
                user_dict = obj_in.dict(exclude={"password"})
                for key, value in user_dict.items():
                    user_data[key] = value
            else:
                # Si es un diccionario
                for key, value in obj_in.items():
                    if key != "password":
                        user_data[key] = value

            # Añadir la contraseña hasheada
            user_data["password_hash"] = hashed_password

            db_obj = User(**user_data)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            logger.error(f"Error en create_with_hashed_password: {e}")
            db.rollback()
            return None


# Instanciar repositorio
user_repository = UserRepository(User)
