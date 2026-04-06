# =========================
# Estados del registro de aliados (flujo unificado)
# =========================
(
    ALLY_NAME,
    ALLY_OWNER,
    ALLY_DOCUMENT,
    ALLY_PHONE,
    ALLY_CITY,
    ALLY_BARRIO,
    ALLY_ADDRESS,
    ALLY_UBICACION,
    ALLY_CONFIRM,
    ALLY_TEAM,
) = range(10)


# =========================
# Estados para registro de repartidores (flujo unificado)
# =========================
(
    COURIER_FULLNAME,
    COURIER_IDNUMBER,
    COURIER_PHONE,
    COURIER_CITY,
    COURIER_BARRIO,
    COURIER_RESIDENCE_ADDRESS,
    COURIER_RESIDENCE_LOCATION,
    COURIER_PLATE,
    COURIER_BIKETYPE,
    COURIER_CEDULA_FRONT,
    COURIER_CEDULA_BACK,
    COURIER_SELFIE,
    COURIER_CONFIRM,
    COURIER_TEAM,
) = range(100, 114)

COURIER_VEHICLE_TYPE = 114  # Selección de vehículo: Moto o Bicicleta


# =========================
# Estados para registro de administrador local (flujo unificado)
# =========================
(
    LOCAL_ADMIN_NAME,
    LOCAL_ADMIN_DOCUMENT,
    LOCAL_ADMIN_TEAMNAME,
    LOCAL_ADMIN_PHONE,
    LOCAL_ADMIN_CITY,
    LOCAL_ADMIN_BARRIO,
    LOCAL_ADMIN_RESIDENCE_ADDRESS,
    LOCAL_ADMIN_RESIDENCE_LOCATION,
    LOCAL_ADMIN_CEDULA_FRONT,
    LOCAL_ADMIN_CEDULA_BACK,
    LOCAL_ADMIN_SELFIE,
    LOCAL_ADMIN_CONFIRM,
) = range(300, 312)


FLOW_STATE_ORDER = {
    "ally": [
        ALLY_NAME, ALLY_OWNER, ALLY_DOCUMENT, ALLY_PHONE,
        ALLY_CITY, ALLY_BARRIO, ALLY_UBICACION, ALLY_CONFIRM,
    ],
    "courier": [
        COURIER_FULLNAME, COURIER_IDNUMBER, COURIER_PHONE,
        COURIER_CITY, COURIER_BARRIO, COURIER_RESIDENCE_LOCATION,
        COURIER_VEHICLE_TYPE, COURIER_PLATE, COURIER_BIKETYPE,
        COURIER_CEDULA_FRONT, COURIER_CEDULA_BACK, COURIER_SELFIE,
        COURIER_CONFIRM,
    ],
    "admin": [
        LOCAL_ADMIN_NAME, LOCAL_ADMIN_DOCUMENT, LOCAL_ADMIN_TEAMNAME,
        LOCAL_ADMIN_PHONE, LOCAL_ADMIN_CITY, LOCAL_ADMIN_BARRIO,
        LOCAL_ADMIN_RESIDENCE_LOCATION,
        LOCAL_ADMIN_CEDULA_FRONT, LOCAL_ADMIN_CEDULA_BACK, LOCAL_ADMIN_SELFIE,
        LOCAL_ADMIN_CONFIRM,
    ],
}

FLOW_STATE_KEYS = {
    "ally": {
        ALLY_NAME: ["business_name"],
        ALLY_OWNER: ["owner_name"],
        ALLY_DOCUMENT: ["ally_document"],
        ALLY_PHONE: ["ally_phone"],
        ALLY_CITY: ["city"],
        ALLY_BARRIO: ["barrio"],
        ALLY_UBICACION: ["address", "ally_lat", "ally_lng"],
        ALLY_CONFIRM: [],
    },
    "courier": {
        COURIER_FULLNAME: ["full_name"],
        COURIER_IDNUMBER: ["id_number"],
        COURIER_PHONE: ["phone"],
        COURIER_CITY: ["city"],
        COURIER_BARRIO: ["barrio"],
        COURIER_RESIDENCE_LOCATION: ["residence_address", "residence_lat", "residence_lng"],
        COURIER_VEHICLE_TYPE: ["vehicle_type"],
        COURIER_PLATE: ["plate"],
        COURIER_BIKETYPE: ["bike_type"],
        COURIER_CEDULA_FRONT: ["cedula_front_file_id"],
        COURIER_CEDULA_BACK: ["cedula_back_file_id"],
        COURIER_SELFIE: ["selfie_file_id"],
        COURIER_CONFIRM: [],
    },
    "admin": {
        LOCAL_ADMIN_NAME: ["admin_name"],
        LOCAL_ADMIN_DOCUMENT: ["admin_document"],
        LOCAL_ADMIN_TEAMNAME: ["admin_team_name"],
        LOCAL_ADMIN_PHONE: ["phone"],
        LOCAL_ADMIN_CITY: ["admin_city"],
        LOCAL_ADMIN_BARRIO: ["admin_barrio"],
        LOCAL_ADMIN_RESIDENCE_LOCATION: ["admin_residence_address", "admin_residence_lat", "admin_residence_lng"],
        LOCAL_ADMIN_CEDULA_FRONT: ["admin_cedula_front_file_id"],
        LOCAL_ADMIN_CEDULA_BACK: ["admin_cedula_back_file_id"],
        LOCAL_ADMIN_SELFIE: ["admin_selfie_file_id"],
        LOCAL_ADMIN_CONFIRM: [],
    },
}

FLOW_PREVIOUS_STATE = {}
for _flow, _states in FLOW_STATE_ORDER.items():
    FLOW_PREVIOUS_STATE[_flow] = {}
    for _idx, _state in enumerate(_states):
        FLOW_PREVIOUS_STATE[_flow][_state] = _states[_idx - 1] if _idx > 0 else None


# =========================
# Estados para crear un pedido (modificado para cliente recurrente)
# =========================
(
    PEDIDO_SELECTOR_CLIENTE,      # Selector cliente recurrente/nuevo
    PEDIDO_BUSCAR_CLIENTE,        # Buscar cliente por nombre/telefono
    PEDIDO_SELECCIONAR_DIRECCION, # Seleccionar direccion del cliente
    PEDIDO_INSTRUCCIONES_EXTRA,   # Preguntar si agregar instrucciones adicionales
    PEDIDO_TIPO_SERVICIO,
    PEDIDO_NOMBRE,
    PEDIDO_TELEFONO,
    PEDIDO_UBICACION,             # Capturar ubicacion (link/coords) opcional
    PEDIDO_DIRECCION,
    PEDIDO_PICKUP_SELECTOR,       # Selector de punto de recogida
    PEDIDO_PICKUP_LISTA,          # Lista de pickups guardados
    PEDIDO_PICKUP_NUEVA_UBICACION,# Capturar coords de nueva direccion
    PEDIDO_PICKUP_NUEVA_DETALLES, # Capturar detalles de nueva direccion
    PEDIDO_PICKUP_GUARDAR,        # Preguntar si guardar nueva direccion
    PEDIDO_REQUIERE_BASE,         # Preguntar si requiere base
    PEDIDO_VALOR_BASE,            # Capturar valor de base
    PEDIDO_CONFIRMACION,
    PEDIDO_GUARDAR_CLIENTE,       # Preguntar si guardar cliente nuevo
    PEDIDO_COMPRAS_CANTIDAD,      # Capturar lista de productos con cantidades
) = range(14, 33)

PEDIDO_INCENTIVO_MONTO = 900  # Capturar incentivo adicional (otro monto)
PEDIDO_PICKUP_NUEVA_CIUDAD = 880
PEDIDO_PICKUP_NUEVA_BARRIO = 881


# =========================
# Estados para crear una ruta multi-parada
# =========================
(
    RUTA_PICKUP_SELECTOR,        # 33 - Selector de punto de recogida
    RUTA_PICKUP_LISTA,           # 34 - Lista de pickups guardados
    RUTA_PICKUP_NUEVA_UBICACION, # 35 - Capturar coords nueva direccion de recogida
    RUTA_PICKUP_NUEVA_DETALLES,  # 36 - Detalles de nueva direccion
    RUTA_PICKUP_GUARDAR,         # 37 - Preguntar si guardar nueva direccion
    RUTA_PARADA_SELECTOR,        # 38 - Tipo de cliente (nuevo/recurrente) para parada actual
    RUTA_PARADA_SEL_DIRECCION,   # 39 - Seleccionar direccion de cliente recurrente
    RUTA_PARADA_NOMBRE,          # 40 - Nombre del cliente
    RUTA_PARADA_TELEFONO,        # 41 - Telefono del cliente
    RUTA_PARADA_UBICACION,       # 42 - GPS opcional de la parada
    RUTA_PARADA_DIRECCION,       # 43 - Direccion de entrega
    RUTA_MAS_PARADAS,            # 44 - Agregar mas paradas o finalizar
    RUTA_DISTANCIA_KM,           # 45 - Km totales (si no hay GPS suficiente)
    RUTA_CONFIRMACION,           # 46 - Confirmacion y creacion de la ruta
    RUTA_GUARDAR_CLIENTES,       # 47 - Guardar clientes nuevos de las paradas
) = range(33, 48)

RUTA_PICKUP_NUEVA_CIUDAD = 48
RUTA_PICKUP_NUEVA_BARRIO = 49
RUTA_PARADA_CIUDAD = 50
RUTA_PARADA_BARRIO = 51
RUTA_PARADA_BUSCAR = 52   # Buscar cliente por nombre/telefono en parada de ruta
RUTA_PARADA_DEDUP  = 53   # Confirmar cliente existente encontrado por telefono en ruta


# =========================
# Estados para /clientes (agenda de clientes recurrentes)
# =========================
(
    CLIENTES_MENU,
    CLIENTES_NUEVO_NOMBRE,
    CLIENTES_NUEVO_TELEFONO,
    CLIENTES_NUEVO_NOTAS,
    CLIENTES_NUEVO_DIRECCION_LABEL,
    CLIENTES_NUEVO_DIRECCION_TEXT,
    CLIENTES_BUSCAR,
    CLIENTES_VER_CLIENTE,
    CLIENTES_EDITAR_NOMBRE,
    CLIENTES_EDITAR_TELEFONO,
    CLIENTES_EDITAR_NOTAS,
    CLIENTES_DIR_NUEVA_LABEL,
    CLIENTES_DIR_NUEVA_TEXT,
    CLIENTES_DIR_EDITAR_LABEL,
    CLIENTES_DIR_EDITAR_TEXT,
    CLIENTES_DIR_EDITAR_NOTA,
) = range(400, 416)

CLIENTES_DIR_CIUDAD = 416
CLIENTES_DIR_BARRIO = 417
CLIENTES_DIR_CORREGIR_COORDS = 418
CLIENTES_DIR_CORREGIR_GEO = 419


# =========================
# Estados para /direcciones (panel Mis direcciones del aliado)
# =========================
(
    DIRECCIONES_MENU,
    DIRECCIONES_PICKUPS,
    DIRECCIONES_PICKUP_NUEVA_UBICACION,
    DIRECCIONES_PICKUP_NUEVA_DETALLES,
    DIRECCIONES_PICKUP_GUARDAR,
) = range(500, 505)

DIRECCIONES_PICKUP_NUEVA_CIUDAD = 505
DIRECCIONES_PICKUP_NUEVA_BARRIO = 506

# =========================
# Estados para cotizador interno
# =========================
COTIZAR_DISTANCIA = 901
COTIZAR_MODO = 903
COTIZAR_RECOGIDA = 904
COTIZAR_ENTREGA = 905
COTIZAR_RECOGIDA_SELECTOR = 906
COTIZAR_RESULTADO = 907


# =========================
# Estados para configuración de tarifas (Admin Plataforma)
# =========================
TARIFAS_VALOR = 902

# =========================
# Estados para sistema de recargas
# =========================
RECARGAR_MONTO = 950
RECARGAR_ADMIN = 951
RECARGAR_COMPROBANTE = 952
RECARGAR_ROL = 953

CONFIG_ALLY_SUBSIDY_VALOR = 956  # Capturar nuevo subsidio de domicilio del aliado

# =========================
# Estados para configurar datos de pago
# =========================
PAGO_TELEFONO = 960
PAGO_BANCO = 961
PAGO_TITULAR = 962
PAGO_INSTRUCCIONES = 963
PAGO_MENU = 964
ALERTAS_OFERTA_INPUT = 965

# Estados para el flujo de registro de ingreso externo (Admin Plataforma)
INGRESO_MONTO = 970
INGRESO_METODO = 971
INGRESO_NOTA = 972

# Estado para el flujo de retiro de Sociedad → saldo personal (Admin Plataforma)
SOCIEDAD_RETIRO_MONTO = 973

OFFER_SUGGEST_INC_MONTO = 915  # Capturar monto libre en sugerencia T+5 (pedido)
ROUTE_SUGGEST_INC_MONTO = 914  # Capturar monto libre en sugerencia T+5 (ruta)

# Estados para pedido especial del Admin Local
ADMIN_PEDIDO_PICKUP    = 908   # Seleccionar/crear dirección de recogida
ADMIN_PEDIDO_CUST_NAME = 909   # Nombre del cliente
ADMIN_PEDIDO_CUST_PHONE= 910   # Teléfono del cliente
ADMIN_PEDIDO_CUST_ADDR = 911   # Dirección de entrega (texto/GPS/geocoding)
ADMIN_PEDIDO_TARIFA    = 912   # Tarifa manual al repartidor (ingresada por el admin)
ADMIN_PEDIDO_INSTRUC   = 913   # Instrucciones adicionales
ADMIN_PEDIDO_INC_MONTO = 916   # Incentivo adicional (monto libre pre-publicación)
ADMIN_PEDIDO_COMISION  = 1011  # Comisión especial que el admin cobra al repartidor por el servicio
ADMIN_PEDIDO_TEMPLATE_NAME = 1012  # Nombre de la plantilla al guardar pedido especial como plantilla
ADMIN_PEDIDO_USE_TEMPLATE  = 1013  # Seleccionar plantilla para pre-llenar pedido especial
RECHAZAR_MOTIVO            = 1014  # Capturar motivo de rechazo (rechazar_conv)
RECHAZAR_CONFIRMAR         = 1015  # Confirmacion antes de pedir motivo (rechazar_conv)

# Estados para el panel de gestión de ubicaciones del aliado
ALLY_LOCS_MENU       = 920   # Panel principal (lista + operaciones vía callbacks)
ALLY_LOCS_ADD_COORDS = 921   # Agregar: esperando GPS / link / coords
ALLY_LOCS_ADD_LABEL  = 922   # Agregar: esperando etiqueta / nombre
ALLY_LOCS_ADD_CITY   = 923   # Agregar: esperando ciudad
ALLY_LOCS_ADD_BARRIO = 924   # Agregar: esperando barrio/sector

# =========================
# Estados para agenda de clientes del Admin Local/Plataforma
# =========================
ADMIN_CUST_MENU              = 925
ADMIN_CUST_NUEVO_NOMBRE      = 926
ADMIN_CUST_NUEVO_TELEFONO    = 927
ADMIN_CUST_NUEVO_NOTAS       = 928
ADMIN_CUST_NUEVO_DIR_LABEL   = 929
ADMIN_CUST_NUEVO_DIR_TEXT    = 930
ADMIN_CUST_BUSCAR            = 931
ADMIN_CUST_VER               = 932
ADMIN_CUST_EDITAR_NOMBRE     = 933
ADMIN_CUST_EDITAR_TELEFONO   = 934
ADMIN_CUST_EDITAR_NOTAS      = 935
ADMIN_CUST_DIR_NUEVA_LABEL   = 936
ADMIN_CUST_DIR_NUEVA_TEXT    = 937
ADMIN_CUST_DIR_EDITAR_LABEL  = 938
ADMIN_CUST_DIR_EDITAR_TEXT   = 939
ADMIN_CUST_DIR_EDITAR_NOTA   = 940
ADMIN_CUST_DIR_CIUDAD        = 941
ADMIN_CUST_DIR_BARRIO        = 942
ADMIN_CUST_DIR_CORREGIR      = 943

# =========================
# Estados para gestion de ubicaciones de recogida del Admin (Mis Direcciones)
# =========================
ADMIN_DIRS_MENU         = 945
ADMIN_DIRS_NUEVA_LABEL  = 946
ADMIN_DIRS_NUEVA_TEXT   = 947
ADMIN_DIRS_NUEVA_TEL    = 948
ADMIN_DIRS_VER          = 949

# =========================
# Agenda de clientes del aliado (ally_clientes_conv)
# Prefijo callbacks: allycust_  |  Prefijo user_data: allycust_
# =========================
ALLY_CUST_MENU           = 973
ALLY_CUST_NUEVO_NOMBRE   = 974
ALLY_CUST_NUEVO_TEL      = 975
ALLY_CUST_NUEVO_NOTAS    = 976
ALLY_CUST_NUEVO_DIR_LABEL = 977
ALLY_CUST_NUEVO_DIR_TEXT  = 978
ALLY_CUST_BUSCAR         = 979
ALLY_CUST_VER            = 980
ALLY_CUST_EDITAR_NOMBRE  = 981
ALLY_CUST_EDITAR_TEL     = 982
ALLY_CUST_EDITAR_NOTAS   = 983
ALLY_CUST_DIR_NUEVA_LABEL = 984
ALLY_CUST_DIR_NUEVA_TEXT  = 985
ALLY_CUST_DIR_EDITAR_LABEL = 986
ALLY_CUST_DIR_EDITAR_TEXT  = 987
ALLY_CUST_DIR_EDITAR_NOTA  = 988
ALLY_CUST_DIR_CIUDAD     = 989
ALLY_CUST_DIR_BARRIO     = 990
ALLY_CUST_DIR_CORREGIR   = 991

PEDIDO_VALOR_COMPRA = 992  # Confirmar/corregir valor de compra declarado por cliente (bandeja)
CONFIG_ALLY_MIN_PURCHASE_VALOR = 993  # Capturar nuevo mínimo de compra para subsidio condicional

# =========================
# Estados para seleccion de cliente/direccion en pedido admin
# =========================
ADMIN_PEDIDO_SEL_CUST      = 917
ADMIN_PEDIDO_SEL_CUST_ADDR = 918
ADMIN_PEDIDO_SAVE_PICKUP   = 919   # Preguntar si guardar nueva direccion de recogida

# =========================
# Suscripciones mensuales
# =========================
CONFIG_SUBS_PRECIO  = 994   # Admin ingresa precio de suscripcion para su aliado
ALLY_SUBS_CONFIRMAR = 995   # Aliado confirma renovacion de suscripcion
RUTA_INCENTIVO_MONTO = 996   # Capturar incentivo adicional libre en ruta (antes de confirmar)

# =========================
# Estados para mejoras de agenda de clientes (2026-03-25)
# =========================
PEDIDO_DEDUP_CONFIRM         = 997   # Confirmar uso de cliente existente hallado por telefono en nuevo_pedido
PEDIDO_GUARDAR_DIR_EXISTENTE = 998   # Ofrecer agregar nueva direccion a cliente ya existente
ADMIN_PEDIDO_SEL_CUST_BUSCAR = 999   # Buscar cliente en agenda durante admin_pedido_conv
ADMIN_PEDIDO_CUST_DEDUP      = 1000  # Confirmar cliente existente hallado por telefono en admin_pedido
ADMIN_PEDIDO_GUARDAR_CUST    = 1001  # Ofrecer guardar cliente nuevo tras crear pedido admin

# =========================

# Estados para agregar paradas extra a un pedido simple (conversion a ruta antes de confirmar)
# =========================
PEDIDO_PARADA_EXTRA_NOMBRE    = 1002  # Nombre del cliente de la parada adicional
PEDIDO_PARADA_EXTRA_TELEFONO  = 1003  # Telefono del cliente de la parada adicional
PEDIDO_PARADA_EXTRA_DIRECCION = 1004  # Direccion (texto, GPS, geo confirm) de la parada adicional

# Estados para flujo de dificultad de parqueo (2026-03-26/27)
# =========================
ALLY_CUST_PARKING          = 1005  # Pregunta al aliado (agenda) si hay dificultad de parqueo
ADMIN_CUST_PARKING         = 1006  # Pregunta al admin (agenda) si hay dificultad de parqueo
PEDIDO_GUARDAR_DIR_PARKING = 1007  # Dificultad de parqueo al guardar nueva dir para cliente existente mid-pedido
PEDIDO_GUARDAR_CUST_PARKING = 1008 # Dificultad de parqueo al guardar cliente nuevo tras crear pedido
ADMIN_PEDIDO_GUARDAR_PARKING = 1009 # Dificultad de parqueo al guardar cliente tras pedido especial admin
RUTA_GUARDAR_CUST_PARKING  = 1010  # Dificultad de parqueo al guardar cliente de parada en ruta

# =========================
# Estados para recarga directa por Admin Plataforma (recarga_directa_conv)
# Prefijo callbacks: plat_rdir_   |  Prefijo user_data: recdir_
# =========================
RECARGA_DIR_TIPO   = 1016  # Seleccion de tipo (COURIER/ALLY/ADMIN) via callbacks
RECARGA_DIR_BUSCAR = 1019  # Texto de busqueda por nombre + seleccion de usuario via callbacks
RECARGA_DIR_MONTO  = 1017  # Texto con el monto a recargar
RECARGA_DIR_NOTA   = 1018  # Texto con nota opcional + confirmacion via callbacks
