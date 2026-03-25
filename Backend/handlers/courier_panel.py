# =============================================================================
# handlers/courier_panel.py — Panel de ganancias del repartidor
# Extraído de main.py
# =============================================================================

from datetime import datetime, timezone, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from services import (
    courier_get_earnings_by_date_key,
    courier_get_earnings_history,
    courier_get_earnings_by_period,
)

_DIAS_ES = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
_MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _fmt_pesos(amount: int) -> str:
    try:
        amount = int(amount or 0)
    except Exception:
        amount = 0
    return f"${amount:,}".replace(",", ".")


def _fmt_date_es(date_key):
    """Convierte YYYY-MM-DD a 'Lun 24 mar'."""
    try:
        dt = datetime.strptime(date_key, "%Y-%m-%d")
        return "{} {} {}".format(_DIAS_ES[dt.weekday()], dt.day, _MESES_ES[dt.month - 1])
    except Exception:
        return date_key


def _courier_period_range(period):
    """Retorna (start_s, end_s, label) para el periodo dado (hoy/ayer/semana/mes)."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "hoy":
        start, end, label = today, today + timedelta(days=1), "Hoy"
    elif period == "ayer":
        start, end, label = today - timedelta(days=1), today, "Ayer"
    elif period == "semana":
        start = today - timedelta(days=today.weekday())
        end = today + timedelta(days=1)
        label = "Esta semana"
    elif period == "mes":
        start = today.replace(day=1)
        end = today + timedelta(days=1)
        label = "Este mes"
    else:
        return None, None, "Periodo desconocido"
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S"), label


def _courier_period_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Hoy", callback_data="courier_earn_periodo_hoy"),
            InlineKeyboardButton("Ayer", callback_data="courier_earn_periodo_ayer"),
        ],
        [
            InlineKeyboardButton("Esta semana", callback_data="courier_earn_periodo_semana"),
            InlineKeyboardButton("Este mes", callback_data="courier_earn_periodo_mes"),
        ],
    ])


def _courier_earnings_group_by_date(rows: list) -> list:
    totals = {}
    for r in rows or []:
        date_key = (r.get("date_key") or "").strip()
        if not date_key:
            continue
        d = totals.setdefault(date_key, {"orders": 0, "gross": 0, "fee": 0, "net": 0})
        d["orders"] += 1
        d["gross"] += int(r.get("gross_amount") or 0)
        d["fee"] += int(r.get("platform_fee") or 0)
        d["net"] += int(r.get("net_amount") or 0)
    result = []
    for k in sorted(totals.keys(), reverse=True):
        row = totals[k]
        result.append({
            "date_key": k,
            "orders": row["orders"],
            "gross": row["gross"],
            "fee": row["fee"],
            "net": row["net"],
        })
    return result


def _courier_period_summary_text(rows, label):
    """Genera texto de resumen para periodos cortos (Hoy/Ayer): lista plana de servicios."""
    if not rows:
        return "Mis ganancias — {}\nNo hay servicios entregados en este periodo.".format(label)

    total_orders = len(rows)
    total_gross = sum(int(r.get("gross_amount") or 0) for r in rows)
    total_fee = sum(int(r.get("platform_fee") or 0) for r in rows)
    total_net = sum(int(r.get("net_amount") or 0) for r in rows)

    lines = [
        "Mis ganancias — {}".format(label),
        "",
        "Servicios entregados: {}".format(total_orders),
        "Bruto: {}".format(_fmt_pesos(total_gross)),
        "Fee plataforma: {}".format(_fmt_pesos(total_fee)),
        "Neto estimado: {}".format(_fmt_pesos(total_net)),
        "",
        "Detalle:",
    ]
    for r in rows[:30]:
        order_id = r.get("order_id")
        hour_key = r.get("hour_key") or "--:--"
        customer = r.get("customer_name") or "N/A"
        lines.append("#{} {} — {} — Neto {}".format(
            order_id, hour_key, customer, _fmt_pesos(int(r.get("net_amount") or 0))
        ))
    if len(rows) > 30:
        lines.append("... y {} mas.".format(len(rows) - 30))

    return "\n".join(lines)


def _courier_period_grouped_text(daily, label):
    """Genera texto agrupado por dia para Esta semana / Este mes."""
    total_orders = sum(d["orders"] for d in daily)
    total_gross = sum(d["gross"] for d in daily)
    total_fee = sum(d["fee"] for d in daily)
    total_net = sum(d["net"] for d in daily)

    lines = [
        "Mis ganancias — {}".format(label),
        "",
        "Servicios entregados: {}".format(total_orders),
        "Bruto: {}".format(_fmt_pesos(total_gross)),
        "Fee plataforma: {}".format(_fmt_pesos(total_fee)),
        "Neto estimado: {}".format(_fmt_pesos(total_net)),
        "",
        "Toca un dia para ver el detalle:",
    ]
    for d in daily:
        lines.append("{} — {} servicios — Neto {}".format(
            _fmt_date_es(d["date_key"]), d["orders"], _fmt_pesos(d["net"])
        ))
    return "\n".join(lines)


def courier_earnings_start(update, context):
    """Muestra selector de periodo para ganancias del repartidor."""
    update.message.reply_text(
        "Mis ganancias\nSelecciona un periodo:",
        reply_markup=_courier_period_keyboard(),
    )


def courier_earnings_callback(update, context):
    """Callback para navegacion de ganancias del repartidor.

    Patrones manejados:
      courier_earn_periodo_{period}        — muestra resumen del periodo
      courier_earn_{YYYYMMDD}_{period}     — dia especifico con volver al periodo
      courier_earn_{YYYYMMDD}              — dia especifico (legacy/compat)
      courier_earn_back | courier_earn_refresh — vuelve al selector de periodo
    """
    query = update.callback_query
    query.answer()
    data = query.data or ""
    telegram_id = update.effective_user.id

    # Volver al selector de periodo
    if data in ("courier_earn_back", "courier_earn_refresh"):
        query.edit_message_text(
            "Mis ganancias\nSelecciona un periodo:",
            reply_markup=_courier_period_keyboard(),
        )
        return

    # Seleccion de periodo
    if data.startswith("courier_earn_periodo_"):
        period = data[len("courier_earn_periodo_"):]
        start_s, end_s, label = _courier_period_range(period)
        if not start_s:
            query.edit_message_text("Periodo invalido.", reply_markup=_courier_period_keyboard())
            return
        ok, courier, rows, msg = courier_get_earnings_by_period(telegram_id, start_s, end_s)
        if not ok:
            query.edit_message_text(msg, reply_markup=_courier_period_keyboard())
            return
        if period in ("hoy", "ayer"):
            text = _courier_period_summary_text(rows, label)
            query.edit_message_text(text, reply_markup=_courier_period_keyboard())
        else:
            daily = _courier_earnings_group_by_date(rows)
            if not daily:
                query.edit_message_text(
                    "Mis ganancias — {}\nNo hay servicios entregados en este periodo.".format(label),
                    reply_markup=_courier_period_keyboard(),
                )
                return
            text = _courier_period_grouped_text(daily, label)
            day_buttons = []
            for d in daily:
                compact = d["date_key"].replace("-", "")
                day_buttons.append([InlineKeyboardButton(
                    _fmt_date_es(d["date_key"]),
                    callback_data="courier_earn_{}_{}".format(compact, period),
                )])
            full_kb = InlineKeyboardMarkup(day_buttons + _courier_period_keyboard().inline_keyboard)
            query.edit_message_text(text, reply_markup=full_kb)
        return

    # Detalle de dia especifico: courier_earn_{YYYYMMDD}_{period} o courier_earn_{YYYYMMDD}
    if not data.startswith("courier_earn_"):
        query.edit_message_text("Accion invalida.", reply_markup=_courier_period_keyboard())
        return

    rest = data[len("courier_earn_"):]
    parts = rest.split("_", 1)
    compact = parts[0]
    parent_period = parts[1] if len(parts) > 1 else None

    if not compact.isdigit() or len(compact) != 8:
        query.edit_message_text("Fecha invalida.", reply_markup=_courier_period_keyboard())
        return

    date_key = "{}-{}-{}".format(compact[0:4], compact[4:6], compact[6:8])
    ok, courier, rows, msg = courier_get_earnings_by_date_key(telegram_id, date_key)
    if not ok:
        query.edit_message_text(msg, reply_markup=_courier_period_keyboard())
        return

    if not rows:
        query.edit_message_text(
            "No hay registros para {}.".format(_fmt_date_es(date_key)),
            reply_markup=_courier_period_keyboard(),
        )
        return

    gross = sum(int(r.get("gross_amount") or 0) for r in rows)
    fee = sum(int(r.get("platform_fee") or 0) for r in rows)
    net = sum(int(r.get("net_amount") or 0) for r in rows)

    lines = [
        "Detalle — {}".format(_fmt_date_es(date_key)),
        "",
        "Servicios: {}".format(len(rows)),
        "Bruto: {}".format(_fmt_pesos(gross)),
        "Fee plataforma: {}".format(_fmt_pesos(fee)),
        "Neto estimado: {}".format(_fmt_pesos(net)),
        "",
        "Servicios:",
    ]
    for r in rows[:25]:
        order_id = r.get("order_id")
        hour_key = r.get("hour_key") or "--:--"
        lines.append("#{} {} | Bruto {} | Fee {} | Neto {}".format(
            order_id,
            hour_key,
            _fmt_pesos(int(r.get("gross_amount") or 0)),
            _fmt_pesos(int(r.get("platform_fee") or 0)),
            _fmt_pesos(int(r.get("net_amount") or 0)),
        ))
    if len(rows) > 25:
        lines.append("... y {} mas.".format(len(rows) - 25))

    # Boton volver al periodo padre (si existe) + selector de periodo
    back_rows = []
    if parent_period in ("semana", "mes"):
        back_label = "Volver a semana" if parent_period == "semana" else "Volver a mes"
        back_rows = [[InlineKeyboardButton(
            back_label,
            callback_data="courier_earn_periodo_{}".format(parent_period),
        )]]
    full_kb = InlineKeyboardMarkup(back_rows + _courier_period_keyboard().inline_keyboard)
    query.edit_message_text("\n".join(lines), reply_markup=full_kb)
