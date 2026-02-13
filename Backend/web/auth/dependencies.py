def get_current_user():
    """
    Simulación de usuario autenticado.

    Esta función actúa como una dependencia de FastAPI.
    Por ahora retorna un usuario fijo para permitir
    el desarrollo y prueba de endpoints protegidos.

    En el futuro:
    - Se reemplazará por validación JWT o sesión real
    - Se obtendrá el usuario desde el token o la BD
    """

    # Clase interna que representa al usuario autenticado
    # Se usa solo como mock temporal
    class User:
        # Identificador único del usuario
        id = 1

        # Rol del usuario (administrador de la plataforma)
        # Se usa para validaciones de permisos
        role = "ADMIN_PLATFORM"

        # Estado del usuario dentro del sistema
        # Indica que el usuario está aprobado y activo
        status = "APPROVED"

    # Retorna una instancia del usuario simulado
    return User()
