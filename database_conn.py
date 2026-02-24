""" Contains Database  """
import sqlite3
import psycopg2
from decouple import config


def get_db_connection_sqlite():
    conn = None
    try:
        conn = sqlite3.connect("database.sqlite")
        return conn
    except sqlite3.error as e:
        print(e)

def get_db_connection_pg():
    conn = psycopg2.connect(
        host=config('DB_HOST'),
        database=config('DB_DATABASE'),
        user=config('DB_USERNAME'),
        password=config('DB_PASSWORD'),
        port=config('DB_PORT')
    )
    return conn