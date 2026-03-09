# BaseModel es la clase base de Pydantic
# Se usa para validar y serializar datos de entrada y salida en la API
from pydantic import BaseModel

# Importa los enums de rol y estado del usuario
# Garantizan que solo se usen valores válidos y consistentes
from web.users.models import UserRole, UserStatus


# Schema de respuesta para un usuario
# Define cómo se enviará un usuario al frontend (API response)
class UserResponse(BaseModel):
    # Identificador único del usuario
    id: int

    # Rol del usuario (enum UserRole)
    role: UserRole

    # Estado del usuario (enum UserStatus)
    status: UserStatus

    class Config:
        # Hace que los enums se serialicen como strings
        # Ejemplo: UserRole.COURIER → "COURIER"
        # Esto es ideal para APIs REST y frontend (Angular)
        use_enum_values = True


# Schema de respuesta para un administrador local
class AdminResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    city: str
    barrio: str
    status: str
    team_name: str
    document_number: str
    created_at: str

    class Config:
        use_enum_values = True


class CourierResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    city: str
    barrio: str
    status: str
    id_number: str
    plate: str
    bike_type: str

    class Config:
        use_enum_values = True


class AllyResponse(BaseModel):
    id: int
    business_name: str
    owner_name: str
    phone: str
    city: str
    barrio: str
    status: str
    address: str

    class Config:
        use_enum_values = True
