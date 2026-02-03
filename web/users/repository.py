def get_user_by_id(user_id: int):
    """
    Obtiene un usuario por su ID.

    Implementación temporal (mock).
    Simula una consulta a base de datos mientras
    se define el modelo real y la conexión a la BD.
    """

    # Clase interna que representa un usuario del sistema
    # Se usa solo como objeto simulado
    class User:
        # ID del usuario solicitado
        id = user_id

        # Rol del usuario
        # En este caso se simula un repartidor
        role = "COURIER"

        # Estado actual del usuario
        # Se simula como pendiente de aprobación
        status = "PENDING"

    # Retorna una instancia del usuario simulado
    return User()
