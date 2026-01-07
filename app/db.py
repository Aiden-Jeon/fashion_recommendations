from __future__ import annotations

import contextvars
import logging
import os
import threading
import time
from functools import wraps
from typing import Any, Callable, Optional

# Load .env file first (for local development)
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from databricks import sql
from databricks.sdk import WorkspaceClient

from settings import get_settings

logger = logging.getLogger("fashion_app.db")

# ============== TTL Cache ==============
_cache: dict[str, tuple[Any, float]] = {}
_cache_lock = threading.Lock()
DEFAULT_CACHE_TTL = 300  # 5 minutes


def cached_query(ttl_seconds: int = DEFAULT_CACHE_TTL):
    """Decorator to cache query results with TTL."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            with _cache_lock:
                if cache_key in _cache:
                    result, cached_time = _cache[cache_key]
                    if time.time() - cached_time < ttl_seconds:
                        logger.debug(f"Cache hit for {func.__name__}")
                        return result
            
            # Cache miss - execute query
            result = func(*args, **kwargs)
            
            with _cache_lock:
                _cache[cache_key] = (result, time.time())
            
            return result
        return wrapper
    return decorator


def clear_cache() -> None:
    """Clear all cached query results."""
    with _cache_lock:
        _cache.clear()
    logger.info("Query cache cleared")

settings = get_settings()
_workspace_client: Optional[WorkspaceClient] = None

# Per-token connection pools so users don't share connections
_pool_lock = threading.Lock()
# key: (access_token, warehouse_id) -> list[sql.Connection]
_connection_pools: dict[tuple[str, str], list[sql.Connection]] = {}
_pool_size = 5

# Cached config
_warehouse_id: Optional[str] = None
_server_hostname: Optional[str] = None
_http_path: Optional[str] = None

# Current request's user token (set this at the top of each request)
_current_access_token: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_access_token", default=None
)


def set_current_user_token(token: Optional[str]) -> None:
    """Set the current request's user access token (from X-Forwarded-Access-Token)."""
    _current_access_token.set(token)


def get_current_user_token() -> Optional[str]:
    """Get the current request's user access token."""
    return _current_access_token.get()


def _get_workspace_client() -> WorkspaceClient:
    """Get or create WorkspaceClient (lazy init to avoid OAuth on import)."""
    global _workspace_client
    if _workspace_client is None:
        _workspace_client = WorkspaceClient()
    return _workspace_client


class TransientDBError(RuntimeError):
    """Raised when a transient database error occurs."""

    pass


def _summarize_exception(exc: BaseException, max_len: int = 300) -> str:
    """Summarize exception message for logging."""
    text = str(exc).strip().replace("\n", " ")
    if len(text) > max_len:
        text = f"{text[:max_len]}…"
    return text or exc.__class__.__name__


def is_transient_db_error(exc: BaseException) -> bool:
    """Check if error is transient and can be retried."""
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "connection",
            "timeout",
            "temporarily unavailable",
            "503",
            "502",
            "504",
            "resource exhausted",
        )
    )


def _get_connection_config() -> tuple[str, str, str]:
    """Get connection configuration (cached)."""
    global _warehouse_id, _server_hostname, _http_path

    if _warehouse_id and _server_hostname and _http_path:
        return _warehouse_id, _server_hostname, _http_path

    w = _get_workspace_client()

    # Prefer the resource-injected env var from the app config
    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
    if not warehouse_id:
        warehouses = list(w.warehouses.list())
        if not warehouses:
            raise RuntimeError("No SQL warehouses available")
        warehouse_id = warehouses[0].id

    server_hostname = w.config.host.replace("https://", "")
    http_path = f"/sql/1.0/warehouses/{warehouse_id}"

    _warehouse_id = warehouse_id
    _server_hostname = server_hostname
    _http_path = http_path

    logger.info(f"Using SQL Warehouse: {warehouse_id}")
    return warehouse_id, server_hostname, http_path


def _create_connection(access_token: str) -> sql.Connection:
    """Create a new database connection for a given user token."""
    _, server_hostname, http_path = _get_connection_config()

    # OBO: pass the user's access token so UC enforces user permissions
    return sql.connect(
        server_hostname=server_hostname,
        http_path=http_path,
        access_token=access_token,
    )


def _get_pool(access_token: str, warehouse_id: str) -> list[sql.Connection]:
    key = (access_token, warehouse_id)
    with _pool_lock:
        return _connection_pools.setdefault(key, [])


def _get_connection(access_token: str) -> sql.Connection:
    """Get a connection from the per-token pool or create a new one."""
    # Fallback to environment variable for local development
    if not access_token:
        access_token = os.getenv("DATABRICKS_TOKEN", "")
    
    if not access_token:
        raise RuntimeError(
            "Missing user access token. Ensure you pass the X-Forwarded-Access-Token "
            "from the request into set_current_user_token(...) before querying, "
            "or set DATABRICKS_TOKEN in your .env file for local development."
        )
    warehouse_id, _, _ = _get_connection_config()
    pool = _get_pool(access_token, warehouse_id)

    with _pool_lock:
        # Try to reuse existing connection
        while pool:
            conn = pool.pop()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchall()
                cursor.close()
                return conn
            except Exception as e:
                logger.warning(
                    f"Discarding stale connection: {_summarize_exception(e)}"
                )
                try:
                    conn.close()
                except Exception:
                    pass

    # Create new connection if pool is empty
    return _create_connection(access_token)


def _return_connection(conn: sql.Connection, access_token: str) -> None:
    """Return a connection to the per-token pool."""
    warehouse_id, _, _ = _get_connection_config()
    pool = _get_pool(access_token, warehouse_id)
    with _pool_lock:
        if len(pool) < _pool_size:
            pool.append(conn)
        else:
            try:
                conn.close()
            except Exception:
                pass


def _clear_all_pools() -> None:
    """Clear all token-scoped pools."""
    with _pool_lock:
        for pool in _connection_pools.values():
            while pool:
                conn = pool.pop()
                try:
                    conn.close()
                except Exception:
                    pass
        _connection_pools.clear()


def with_sql_connection(
    exec_fn: Callable[[sql.Connection], Any],
    max_retries: int = 2,
    access_token: Optional[str] = None,
) -> Any:
    """Execute function with a SQL connection, handling retries."""
    token = access_token or get_current_user_token()
    last_exception: Optional[BaseException] = None

    for attempt in range(max_retries + 1):
        conn: Optional[sql.Connection] = None
        try:
            conn = _get_connection(token or "")
            result = exec_fn(conn)
            _return_connection(conn, token or "")
            return result
        except Exception as exc:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

            msg = str(exc).lower()
            is_transient = is_transient_db_error(exc)
            # On auth errors, don't retry with the same token
            if (
                "401" in msg
                or "unauthorized" in msg
                or "invalid token" in msg
                or "expired" in msg
            ):
                logger.error(
                    "Authorization error when querying with user token; not retrying."
                )
                raise

            last_exception = exc

            if is_transient and attempt < max_retries:
                logger.warning(
                    f"Transient error (attempt {attempt + 1}/{max_retries + 1}): "
                    f"{_summarize_exception(exc)}"
                )
                _clear_all_pools()
                time.sleep(0.5 * (attempt + 1))
                continue

            if is_transient:
                raise TransientDBError(
                    f"SQL query failed after {max_retries + 1} attempts"
                ) from exc

            logger.error(f"Database error: {_summarize_exception(exc)}")
            raise

    raise last_exception  # pragma: no cover


def query_sql(
    query: str, params: Optional[list] = None, access_token: Optional[str] = None
) -> pd.DataFrame:
    """Execute SQL query with the current user's token and return results as DataFrame."""

    def _exec(conn: sql.Connection) -> pd.DataFrame:
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return pd.DataFrame(rows, columns=columns)
            else:
                return pd.DataFrame()
        finally:
            cursor.close()

    try:
        return with_sql_connection(_exec, access_token=access_token)
    except Exception as e:
        logger.error(f"Error executing query: {_summarize_exception(e)}")
        logger.debug(f"Query: {query[:500]}...")
        raise


def close_all_connections() -> None:
    """Close all connections in all per-token pools. Call on app shutdown."""
    logger.info("Closing all database connections")
    _clear_all_pools()
