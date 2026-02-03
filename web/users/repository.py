# Importa los enums que definen roles y estados válidos de un usuario
# Usar enums evita errores por strings mal escritos y centraliza reglas
from web.users.models import UserRole, UserStatus


def get_user_by_id(user_id: int):
    """
    Obtiene un usuario por su ID.

    Implementación temporal (mock).
    Simula una consulta a base de datos mientras
    se define el modelo real y la conexión a la BD.
    """

    # Clase interna que simula la entidad Usuario
    # Se usa solo para pruebas y desarrollo inicial
    class User:
        # ID del usuario solicitado
        id = user_id

        # Rol asignado al usuario (ejemplo: repartidor)
        role = UserRole.COURIER

        # Estado actual del usuario (pendiente de aprobación)
        status = UserStatus.PENDING

    # Retorna la instancia simulada del usuario
    return User()
