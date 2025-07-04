import psycopg2
import json
from datetime import date, datetime

# Połączenie do bazy - ustaw swoje zmienne środowiskowe lub parametry tutaj
conn = psycopg2.connect(
    host="YOUR_HOST",
    database="YOUR_DB",
    user="YOUR_USER",
    password="YOUR_PASSWORD",
    port=5432
)

def json_converter(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(f"Nie mogę serializować obiektu typu {type(o)}")

def load_user():
    with conn.cursor() as cur:
        cur.execute("SELECT data FROM users_data WHERE id = 1;")
        row = cur.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                print("Błąd dekodowania JSON, zwracam pusty słownik")
                return {}
        else:
            return {}

def save_user(data):
    json_data = json.dumps(data, indent=4, default=json_converter)
    with conn.cursor() as cur:
        # Używamy UPSERT, aby wstawić lub zaktualizować rekord
        cur.execute("""
            INSERT INTO users_data (id, data)
            VALUES (1, %s)
            ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
        """, (json_data,))
        conn.commit()
