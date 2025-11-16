# Compatibilidad para entornos donde el módulo estándar imghdr ya no existe (Python 3.13+)
# La librería python-telegram-bot lo usa para detectar el tipo de imagen.
# Aquí devolvemos siempre None, que es suficiente para nuestro bot.

def what(file, h=None):
    return None
