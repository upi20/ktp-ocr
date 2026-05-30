from psycopg_pool import ConnectionPool

from .config import DB_DSN

_pool: ConnectionPool | None = None

_provinces: list[tuple[str, str]] = []
_regencies: list[tuple[str, str, str]] = []
_districts: list[tuple[str, str, str]] = []
_villages: list[tuple[str, str, str]] = []


def init_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(DB_DSN, min_size=1, max_size=4, kwargs={"autocommit": True})
        _pool.wait()
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def load_address_caches() -> None:
    global _provinces, _regencies, _districts, _villages
    pool = init_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name FROM address_provinces")
        _provinces = [(r[0], r[1]) for r in cur.fetchall()]
        cur.execute("SELECT id, province_id, name FROM address_regencies")
        _regencies = [(r[0], r[1], r[2]) for r in cur.fetchall()]
        cur.execute("SELECT id, regency_id, name FROM address_districts")
        _districts = [(r[0], r[1], r[2]) for r in cur.fetchall()]
        cur.execute("SELECT id, district_id, name FROM address_villages")
        _villages = [(r[0], r[1], r[2]) for r in cur.fetchall()]


def get_caches():
    return _provinces, _regencies, _districts, _villages
