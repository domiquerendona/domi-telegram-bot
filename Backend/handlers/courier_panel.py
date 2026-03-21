# =============================================================================
# handlers/courier_panel.py — Panel de ganancias del repartidor
# Extraído de main.py
# =============================================================================

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from services import (
    courier_get_earnings_by_date_key,
    courier_get_earnings_history,
)


def _fmt_pesos(amount: int) -> str:
    try:
        amount = int(amount or 0)
    except Exception:
        amount = 0
    return f"${amount:,}".replace(",", ".")


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
    # Orden desc por fecha (YYYY-MM-DD)
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


def _courier_earnings_buttons(daily: list):
    keyboard = []
    for d in daily:
        date_key = d["date_key"]
        compact = date_key.replace("-", "")
        label = "{} ({} pedidos)".format(date_key, d["orders"])
        keyboard.append([InlineKeyboardButton(label, callback_data="courier_earn_{}".format(compact))])
    keyboard.append([InlineKeyboardButton("Actualizar", callback_data="courier_earn_refresh")])
    return InlineKeyboardMarkup(keyboard)


def courier_earnings_start(update, context):
    """Muestra resumen de ganancias del repartidor por día (según liquidaciones contables)."""
    telegram_id = update.effective_user.id
    ok, courier, rows, msg = courier_get_earnings_history(telegram_id, days=7)
    if not ok:
        update.message.reply_text(msg)
        return

    daily = _courier_earnings_group_by_date(rows)
    if not daily:
        update.message.reply_text("No hay ganancias registradas en los últimos 7 días.")
        return

    total_orders = sum(d["orders"] for d in daily)
    total_gross = sum(d["gross"] for d in daily)
    total_fee = sum(d["fee"] for d in daily)
    total_net = sum(d["net"] for d in daily)

    text = (
        "MIS GANANCIAS (ULTIMOS 7 DIAS)\n\n"
        "Pedidos entregados: {}\n"
        "Bruto: {}\n"
        "Fee plataforma cobrado: {}\n"
        "Neto estimado: {}\n\n"
        "Selecciona un día para ver el detalle:"
    ).format(total_orders, _fmt_pesos(total_gross), _fmt_pesos(total_fee), _fmt_pesos(total_net))

    update.message.reply_text(text, reply_markup=_courier_earnings_buttons(daily))


def courier_earnings_callback(update, context):
    """Callback para ver resumen/detalle de ganancias del repartidor."""
    query = update.callback_query
    query.answer()
    data = query.data or ""
    telegram_id = update.effective_user.id

    if data == "courier_earn_refresh" or data == "courier_earn_back":
        ok, courier, rows, msg = courier_get_earnings_history(telegram_id, days=7)
        if not ok:
            query.edit_message_text(msg)
            return
        daily = _courier_earnings_group_by_date(rows)
        if not daily:
            query.edit_message_text("No hay ganancias registradas en los últimos 7 días.")
            return
        total_orders = sum(d["orders"] for d in daily)
        total_gross = sum(d["gross"] for d in daily)
        total_fee = sum(d["fee"] for d in daily)
        total_net = sum(d["net"] for d in daily)
        text = (
            "MIS GANANCIAS (ULTIMOS 7 DIAS)\n\n"
            "Pedidos entregados: {}\n"
            "Bruto: {}\n"
            "Fee plataforma cobrado: {}\n"
            "Neto estimado: {}\n\n"
            "Selecciona un día para ver el detalle:"
        ).format(total_orders, _fmt_pesos(total_gross), _fmt_pesos(total_fee), _fmt_pesos(total_net))
        query.edit_message_text(text, reply_markup=_courier_earnings_buttons(daily))
        return

    if not data.startswith("courier_earn_"):
        query.edit_message_text("Accion invalida.")
        return

    compact = data[len("courier_earn_"):]
    if not compact.isdigit() or len(compact) != 8:
        query.edit_message_text("Fecha invalida.")
        return

    date_key = "{}-{}-{}".format(compact[0:4], compact[4:6], compact[6:8])
    ok, courier, rows, msg = courier_get_earnings_by_date_key(telegram_id, date_key)
    if not ok:
        query.edit_message_text(msg)
        return

    if not rows:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="courier_earn_back")]])
        query.edit_message_text("No hay registros para {}.".format(date_key), reply_markup=keyboard)
        return

    gross = sum(int(r.get("gross_amount") or 0) for r in rows)
    fee = sum(int(r.get("platform_fee") or 0) for r in rows)
    net = sum(int(r.get("net_amount") or 0) for r in rows)

    lines = [
        "DETALLE DE GANANCIAS",
        "",
        "Fecha: {}".format(date_key),
        "Pedidos: {}".format(len(rows)),
        "Bruto: {}".format(_fmt_pesos(gross)),
        "Fee plataforma cobrado: {}".format(_fmt_pesos(fee)),
        "Neto estimado: {}".format(_fmt_pesos(net)),
        "",
        "Pedidos:",
    ]
    for r in rows[:25]:
        order_id = r.get("order_id")
        hour_key = r.get("hour_key") or "--:--"
        lines.append(
            "#{} {} | Bruto {} | Fee {} | Neto {}".format(
                order_id,
                hour_key,
                _fmt_pesos(int(r.get("gross_amount") or 0)),
                _fmt_pesos(int(r.get("platform_fee") or 0)),
                _fmt_pesos(int(r.get("net_amount") or 0)),
            )
        )
    if len(rows) > 25:
        lines.append("... y {} mas.".format(len(rows) - 25))

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="courier_earn_back")]])
    query.edit_message_text("\n".join(lines), reply_markup=keyboard)


