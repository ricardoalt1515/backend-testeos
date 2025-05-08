from fastapi import Depends
from sqlalchemy.orm import Session
import logging
from contextlib import contextmanager

from app.db.base import get_db

logger = logging.getLogger("hydrous")


class DatabaseContext:
    """Contexto de base de datos para operaciones transaccionales"""

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    @contextmanager
    def transaction(self):
        """
        Proporciona un contexto transaccional que hace commit o rollback automático

        Uso:
            async with database_context.transaction() as db:
                user_repository.create(db, obj_in=user_data)
        """
        try:
            yield self.db
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en transacción: {e}")
            raise


# Instancia para usar como dependencia
database_context = DatabaseContext()
