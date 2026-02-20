# Importa el decorador dataclass para crear clases de datos
from dataclasses import dataclass

# Importa datetime para manejar fechas y horas
from datetime import datetime


@dataclass
class Team:
    """
    Representa un equipo de trabajo dentro del sistema.
    """

    # Identificador único del equipo
    id: int

    # Nombre del equipo
    name: str

    # ID del usuario propietario del equipo
    # Se usa como referencia al usuario (user_id)
    owner_id: int

    # Fecha y hora en la que el equipo fue creado
    created_at: datetime
