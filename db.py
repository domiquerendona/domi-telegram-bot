def ensure_user(telegram_id: int, username: str = None):
    user = get_user_by_telegram_id(telegram_id)
    if user:
        return user

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (telegram_id, username, role)
        VALUES (?, ?, NULL);
    """, (telegram_id, username))
    conn.commit()
    conn.close()
    return get_user_by_telegram_id(telegram_id)
