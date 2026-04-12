# Checklist de Seguridad para el Entorno de Producción

Este documento contiene una lista de verificaciones de seguridad recomendadas para el entorno de producción de Domiquerendona.

## 1. Variables de Entorno y Secretos

- [ ] **`BOT_TOKEN`**: Debe ser único para el entorno de producción y no debe ser el mismo que el de desarrollo.
- [ ] **`DATABASE_URL`**: Debe estar configurada y apuntar a la base de datos de PostgreSQL en producción. El sistema no debe poder arrancar sin esta variable.
- [ ] **`GOOGLE_MAPS_API_KEY`**: Debe estar configurada y tener las restricciones de API adecuadas (ej. restringir por IP o por referer HTTP) en la consola de Google Cloud para evitar su uso no autorizado.
- [ ] **`WEB_SECRET_KEY`**: Debe ser una cadena de texto larga y aleatoria. No debe ser la misma que en desarrollo.
- [ ] **Otras claves de API**: Cualquier otra clave de API o secreto debe ser manejada a través de variables de entorno y nunca estar hardcodeada en el código.

## 2. Seguridad del Sistema de Archivos

- [ ] **`bot_persistence.pkl`**: Los permisos de este archivo deben ser restrictivos. Se recomienda `600` (lectura y escritura solo para el usuario propietario del proceso del bot). Esto previene que otros usuarios del sistema puedan leer la información de sesión de los usuarios.
- [ ] **Archivos de código fuente**: Los archivos de código fuente no necesitan permisos de escritura para el proceso del bot. Se recomienda que sean propiedad de un usuario de despliegue y que el proceso del bot corra con un usuario con menos privilegios que solo tenga permisos de lectura.

## 3. Base de Datos

- [ ] **Acceso a la Base de Datos**: El usuario de la base de datos configurado en la `DATABASE_URL` debe tener los permisos mínimos necesarios. No debe ser un superusuario de PostgreSQL.
- [ ] **Conexiones SSL/TLS**: La conexión a la base de datos de PostgreSQL debe usar SSL/TLS para encriptar la comunicación entre la aplicación y la base de datos. Railway suele manejar esto automáticamente, pero es importante verificarlo.
- [ ] **Backups**: Se deben configurar backups periódicos y automáticos de la base de datos de producción.

## 4. Logging y Monitorización

- [ ] **Nivel de Log**: En producción, el nivel de log debe ser `INFO` o `WARNING`, no `DEBUG`, para evitar la exposición de información sensible en los logs.
- [ ] **No loguear PII**: Verificar que no se esté logueando información de identificación personal (PII) como teléfonos, cédulas, nombres completos, o direcciones exactas, especialmente en niveles de log que puedan estar activos en producción.
- [ ] **Monitorización de Errores**: Configurar un sistema de monitorización de errores (como Sentry, o los propios logs de Railway) para ser alertado de excepciones no capturadas en producción.

## 5. Seguridad de la Aplicación Web (FastAPI)

- [ ] **CORS**: La configuración de CORS debe ser restrictiva y solo permitir los orígenes del frontend de producción.
- [ ] **HTTPS**: La API debe ser servida exclusivamente a través de HTTPS.
- [ ] **Autenticación y Autorización**: Todos los endpoints que exponen datos o realizan acciones sensibles deben estar protegidos y verificar los roles y permisos del usuario autenticado.