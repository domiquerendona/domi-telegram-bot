"""
Router público para el formulario de pedido del aliado.
No requiere autenticación.

Endpoints:
  GET  /form/{token}               — validar token y devolver metadata del aliado
  POST /form/{token}/lookup-phone  — buscar cliente existente por teléfono
  POST /form/{token}/quote         — cotizar domicilio por coordenadas
  POST /form/{token}/submit        — guardar solicitud en bandeja temporal
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import (
    get_ally_by_public_token,
    get_ally_customer_by_phone,
    list_customer_addresses,
    create_ally_form_request,
    get_default_ally_location,
    quote_order_by_coords,
    compute_ally_subsidy,
)

router = APIRouter(prefix="/form", tags=["Form"])


# ─── Schemas ────────────────────────────────────────────────────────────────


class FormInfoResponse(BaseModel):
    valid: bool
    ally_id: int
    ally_name: str
    requires_phone_first: bool
    delivery_subsidy: int
    min_purchase_for_subsidy: Optional[int]
    message: str


class LookupPhoneRequest(BaseModel):
    phone: str


class AddressItem(BaseModel):
    id: int
    label: Optional[str]
    address_text: str
    city: Optional[str]
    barrio: Optional[str]


class LookupPhoneResponse(BaseModel):
    exists: bool
    customer_name: Optional[str]
    addresses: List[AddressItem]
    can_add_new_address: bool
    message: str


class QuoteRequest(BaseModel):
    lat: float
    lng: float


class QuoteResponse(BaseModel):
    ok: bool
    quoted_price: Optional[int]
    subsidio_aliado: Optional[int]
    total_base: Optional[int]
    distance_km: Optional[float]
    subsidy_conditional: bool
    message: str


class SubmitRequest(BaseModel):
    customer_name: str
    customer_phone: str
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_barrio: Optional[str] = None
    notes: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    quoted_price: Optional[int] = None
    incentivo_cliente: Optional[int] = None
    purchase_amount_declared: Optional[int] = None


class SubmitResponse(BaseModel):
    ok: bool
    request_id: int
    status: str
    message: str


# ─── Helper interno ──────────────────────────────────────────────────────────


def _resolve_ally(token: str) -> dict:
    """Valida token y retorna el aliado. Lanza 404 si no es válido o inactivo."""
    ally = get_ally_by_public_token(token)
    if not ally:
        raise HTTPException(status_code=404, detail="Enlace no válido o aliado inactivo.")
    return ally


def _opt_str(value: Optional[str]) -> Optional[str]:
    """Aplica strip a un campo opcional; retorna None si queda vacío."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/{token}", response_model=FormInfoResponse)
def get_form_info(token: str):
    """
    Valida el token y devuelve metadata mínima del aliado.
    El frontend usa esta respuesta para confirmar que el enlace es válido
    y mostrar el nombre del negocio antes de pedir el teléfono al cliente.
    """
    ally = _resolve_ally(token)
    return FormInfoResponse(
        valid=True,
        ally_id=ally["id"],
        ally_name=ally["business_name"],
        requires_phone_first=True,
        delivery_subsidy=int(ally["delivery_subsidy"] or 0),
        min_purchase_for_subsidy=ally.get("min_purchase_for_subsidy"),
        message=(
            "Estamos implementando un sistema más cómodo para hacer tus pedidos. "
            "Gracias por tu colaboración. En próximos pedidos no tendrás que llenar "
            "nuevamente todos tus datos."
        ),
    )


@router.post("/{token}/lookup-phone", response_model=LookupPhoneResponse)
def lookup_phone(token: str, body: LookupPhoneRequest):
    """
    Busca si el cliente ya existe en la agenda del aliado.
    Solo lectura: no crea ni modifica ningún dato.
    """
    if not body.phone.strip():
        raise HTTPException(status_code=422, detail="El teléfono es obligatorio.")

    ally = _resolve_ally(token)
    ally_id = ally["id"]

    customer = get_ally_customer_by_phone(ally_id, body.phone.strip())
    if customer:
        raw_addresses = list_customer_addresses(customer["id"])
        addresses = [
            AddressItem(
                id=r["id"],
                label=r["label"],
                address_text=r["address_text"],
                city=r["city"],
                barrio=r["barrio"],
            )
            for r in raw_addresses
        ]
        return LookupPhoneResponse(
            exists=True,
            customer_name=customer["name"],
            addresses=addresses,
            can_add_new_address=True,
            message="Encontramos tus direcciones guardadas. Puedes usar una o agregar una nueva.",
        )

    return LookupPhoneResponse(
        exists=False,
        customer_name=None,
        addresses=[],
        can_add_new_address=True,
        message="No encontramos registros previos. Continúa con tus datos.",
    )


@router.post("/{token}/quote", response_model=QuoteResponse)
def quote_form(token: str, body: QuoteRequest):
    """
    Calcula una cotización estimada del domicilio.
    Requiere que el aliado tenga una ubicación de recogida con coordenadas.
    No crea pedido ni modifica ningún dato.
    """
    ally = _resolve_ally(token)
    delivery_subsidy = int(ally["delivery_subsidy"] or 0)
    min_purchase = ally.get("min_purchase_for_subsidy")
    is_conditional = (delivery_subsidy > 0 and min_purchase is not None)

    pickup = get_default_ally_location(ally["id"])
    pickup_lat = pickup["lat"] if pickup else None
    pickup_lng = pickup["lng"] if pickup else None

    if pickup_lat is None or pickup_lng is None:
        return QuoteResponse(
            ok=True,
            quoted_price=None,
            subsidio_aliado=None,
            total_base=None,
            distance_km=None,
            subsidy_conditional=is_conditional,
            message="Aún no podemos calcular el valor exacto del domicilio.",
        )

    result = quote_order_by_coords(pickup_lat, pickup_lng, body.lat, body.lng)

    if not result.get("success") or result.get("price") is None:
        return QuoteResponse(
            ok=True,
            quoted_price=None,
            subsidio_aliado=None,
            total_base=None,
            distance_km=result.get("distance_km"),
            subsidy_conditional=is_conditional,
            message="No se pudo calcular el valor en este momento.",
        )

    price = int(result["price"])
    # subsidio incondicional: aplica siempre; condicional: sin purchase_amount → 0 en cotización
    subsidio_efectivo = delivery_subsidy if min_purchase is None else 0
    total_base = max(price - subsidio_efectivo, 0)
    dist = round(result["distance_km"], 1)
    if is_conditional:
        message = (
            "Valor estimado del domicilio: ${:,}. "
            "Subsidio de ${:,} aplica en compras desde ${:,}. "
            "El valor final se confirma al crear el pedido."
        ).format(price, delivery_subsidy, min_purchase)
    else:
        message = "Valor estimado del domicilio: ${:,}".format(total_base)
    return QuoteResponse(
        ok=True,
        quoted_price=price,
        subsidio_aliado=subsidio_efectivo if subsidio_efectivo > 0 else None,
        total_base=total_base,
        distance_km=dist,
        subsidy_conditional=is_conditional,
        message=message,
    )


@router.post("/{token}/submit", response_model=SubmitResponse)
def submit_form(token: str, body: SubmitRequest):
    """
    Guarda la solicitud en la bandeja temporal ally_form_requests.
    No crea pedido. No escribe en agenda definitiva.
    - PENDING_REVIEW:  requiere lat + lng + delivery_address no vacía
    - PENDING_LOCATION: cualquier otro caso
    """
    if not body.customer_phone.strip():
        raise HTTPException(status_code=422, detail="El teléfono del cliente es obligatorio.")
    if not body.customer_name.strip():
        raise HTTPException(status_code=422, detail="El nombre del cliente es obligatorio.")

    ally = _resolve_ally(token)
    ally_id = ally["id"]

    delivery_address = _opt_str(body.delivery_address)
    delivery_city = _opt_str(body.delivery_city)
    delivery_barrio = _opt_str(body.delivery_barrio)
    notes = _opt_str(body.notes)

    has_location = (
        body.lat is not None
        and body.lng is not None
        and delivery_address is not None
    )
    status = "PENDING_REVIEW" if has_location else "PENDING_LOCATION"

    # Validar incentivo_cliente: solo valores permitidos
    _INCENTIVO_ALLOWED = {0, 1000, 2000, 3000}
    incentivo_cliente = body.incentivo_cliente if body.incentivo_cliente is not None else 0
    if incentivo_cliente not in _INCENTIVO_ALLOWED:
        raise HTTPException(
            status_code=422,
            detail=f"incentivo_cliente debe ser uno de {sorted(_INCENTIVO_ALLOWED)}.",
        )

    # Validar purchase_amount_declared: negativo → 422; 0 o None → NULL; positivo → guardar
    purchase_amount_declared = body.purchase_amount_declared
    if purchase_amount_declared is not None and purchase_amount_declared < 0:
        raise HTTPException(
            status_code=422,
            detail="purchase_amount_declared no puede ser negativo.",
        )
    if purchase_amount_declared == 0:
        purchase_amount_declared = None

    # Cotización recalculada en backend (fuente de verdad — body.quoted_price se ignora)
    quoted_price_real = None
    subsidio = None
    total_cliente = None

    if has_location:
        pickup = get_default_ally_location(ally_id)
        pickup_lat = pickup["lat"] if pickup else None
        pickup_lng = pickup["lng"] if pickup else None

        if pickup_lat is not None and pickup_lng is not None:
            try:
                result = quote_order_by_coords(pickup_lat, pickup_lng, body.lat, body.lng)
                if result.get("success") and result.get("price") is not None:
                    quoted_price_real = int(result["price"])
                    delivery_subsidy = int(ally["delivery_subsidy"] or 0)
                    min_purchase = ally.get("min_purchase_for_subsidy")
                    # purchase_amount_declared es dato del cliente, no fuente de verdad.
                    # El subsidio condicional solo se aplica cuando el aliado confirma
                    # el valor de compra en el bot (orders.purchase_amount).
                    # Aquí siempre pasamos None: si hay condición → subsidio = 0.
                    subsidio = compute_ally_subsidy(delivery_subsidy, min_purchase, None)
                    total_base = max(quoted_price_real - subsidio, 0)
                    total_cliente = total_base + incentivo_cliente
            except Exception as _e:
                print("[WARN] submit_form: cotizacion fallida ally={} err={}".format(ally_id, _e), flush=True)
                # solicitud se guarda sin cotización

    request_id = create_ally_form_request(
        ally_id=ally_id,
        customer_name=body.customer_name.strip(),
        customer_phone=body.customer_phone.strip(),
        delivery_address=delivery_address,
        delivery_city=delivery_city,
        delivery_barrio=delivery_barrio,
        notes=notes,
        lat=body.lat,
        lng=body.lng,
        status=status,
        quoted_price=quoted_price_real,
        subsidio_aliado=subsidio,
        incentivo_cliente=incentivo_cliente if quoted_price_real is not None else None,
        total_cliente=total_cliente,
        purchase_amount_declared=purchase_amount_declared,
    )

    if has_location:
        message = "Tu solicitud fue recibida correctamente. El aliado la revisará pronto."
    else:
        message = (
            "Tu solicitud fue recibida, pero necesitamos confirmar la ubicación de entrega. "
            "El aliado se pondrá en contacto contigo."
        )

    return SubmitResponse(ok=True, request_id=request_id, status=status, message=message)
