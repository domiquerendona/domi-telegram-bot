# Importa el decorador dataclass para crear clases de datos simples
from dataclasses import dataclass

# Importa datetime para manejar fechas y horas
from datetime import datetime


@dataclass
class Wallet:
    """
    Billetera virtual del usuario.
    Representa el saldo disponible y su última actualización.
    """

    # ID del usuario propietario de la billetera
    user_id: int

    # Saldo actual de la billetera
    balance: float

    # Fecha y hora de la última modificación del saldo
    updated_at: datetime
