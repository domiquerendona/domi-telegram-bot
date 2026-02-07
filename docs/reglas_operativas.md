# Reglas Operativas del Bot

## Significado de Estados

| Estado | Descripcion |
|--------|-------------|
| PENDING | Registro nuevo, esperando aprobacion |
| APPROVED | Aprobado y activo, puede operar |
| INACTIVE | Desactivado temporalmente, puede reactivarse |
| REJECTED | Rechazado, estado terminal desde UI |

## Matriz de Botones por Estado (UI)

Aplica a: Admins, Aliados, Repartidores

| Status Actual | Botones Visibles | Accion Resultante |
|---------------|------------------|-------------------|
| PENDING | Aprobar, Rechazar | -> APPROVED / -> REJECTED |
| APPROVED | Desactivar | -> INACTIVE |
| INACTIVE | Activar | -> APPROVED |
| REJECTED | (solo Volver) | Estado terminal |

## Excepciones

- Admin con `team_code == "PLATFORM"`: no se pueden modificar sus estados, solo se muestra boton Volver.
- Solo Admin Plataforma APPROVED puede acceder a /admin y usar callbacks admin_* y config_*.
- Admin Local debe estar APPROVED para aprobar/rechazar/bloquear repartidores.

## Responsabilidad de Gestion

| Rol | Se gestiona desde | Prefijo callbacks |
|-----|-------------------|-------------------|
| Admins | Panel /admin -> Gestionar administradores | admin_* |
| Aliados | Panel /admin -> Configuraciones -> Gestionar aliados | config_* |
| Repartidores | Panel /admin -> Configuraciones -> Gestionar repartidores | config_* |
