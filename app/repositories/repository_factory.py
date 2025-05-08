from app.repositories.interfaces.user_repository import IUserRepository
from app.repositories.impl.user_repository_impl import UserRepositoryImpl


class RepositoryFactory:
    """Factory para crear instancias de repositorios"""

    @staticmethod
    def get_user_repository() -> IUserRepository:
        """Obtener repositorio de usuarios"""
        return UserRepositoryImpl()
