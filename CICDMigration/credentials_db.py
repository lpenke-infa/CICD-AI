"""
IDMC credentials store.

Stores IDMC connection credentials in a local SQLite file (one row per org).
Passwords are stored in plain text for now, so the database file should be kept
local and excluded from version control.

The database file lives in the project's 'Database' folder by default; the full
path can be overridden with the IDMC_CREDS_DB_PATH environment variable.
"""
import os
import sqlite3
import datetime
from typing import Optional, List, Dict


# Path to the SQLite credentials file. Defaults to 'Database/idmc_credentials.db'
# in the project root (two levels up from this file).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDS_DB_PATH = os.getenv(
    'IDMC_CREDS_DB_PATH',
    os.path.join(_PROJECT_ROOT, 'Database', 'idmc_credentials.db')
)


# One row per org: OrgName is the unique key (saving the same org updates it).
# Column order: OrgName, Entity, Username, Password, Region.
_CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS Idmc_Credentials (
        OrgName    TEXT    PRIMARY KEY,
        Entity     TEXT,
        Username   TEXT    NOT NULL,
        Password   TEXT    NOT NULL,
        Region     TEXT,
        UpdatedAt  TEXT
    )
"""


def _connect() -> sqlite3.Connection:
    """Open a connection, ensuring the folder and table exist."""
    os.makedirs(os.path.dirname(CREDS_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(CREDS_DB_PATH)
    conn.execute(_CREATE_TABLE_SQL)
    return conn


def save_credentials(
    org_name: str,
    entity: str,
    username: str,
    password: str,
    region: str,
    logger=None
) -> bool:
    """
    Insert or update the credentials for an org (keyed by OrgName).

    If a row for org_name already exists it is overwritten, so there is always
    exactly one row per org. Never raises: logs and returns False on failure.

    Args:
        org_name: IDMC organization name (unique key)
        entity: Free-form entity label/identifier for this org
        username: IDMC username
        password: IDMC password (stored in plain text)
        region: IDMC region (e.g. 'dm-us')
        logger: Optional logger instance

    Returns:
        True if the row was saved, False otherwise.
    """
    conn: Optional[sqlite3.Connection] = None
    try:
        now = datetime.datetime.now().isoformat(timespec='seconds')
        conn = _connect()
        conn.execute(
            """
            INSERT INTO Idmc_Credentials (OrgName, Entity, Username, Password, Region, UpdatedAt)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(OrgName) DO UPDATE SET
                Entity    = excluded.Entity,
                Username  = excluded.Username,
                Password  = excluded.Password,
                Region    = excluded.Region,
                UpdatedAt = excluded.UpdatedAt
            """,
            (org_name, entity, username, password, region, now)
        )
        conn.commit()
        if logger:
            logger.info(f"Saved IDMC credentials for org '{org_name}'")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Failed to save IDMC credentials for org '{org_name}': {str(e)}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_credentials(org_name: str, logger=None) -> Optional[Dict[str, str]]:
    """
    Fetch the stored credentials for an org.

    Args:
        org_name: IDMC organization name
        logger: Optional logger instance

    Returns:
        Dict with keys orgName, entity, username, password, region, updatedAt,
        or None if no row exists (or on error).
    """
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect()
        row = conn.execute(
            "SELECT OrgName, Entity, Username, Password, Region, UpdatedAt "
            "FROM Idmc_Credentials WHERE OrgName = ?",
            (org_name,)
        ).fetchone()
        if not row:
            return None
        return {
            'orgName': row[0],
            'entity': row[1],
            'username': row[2],
            'password': row[3],
            'region': row[4],
            'updatedAt': row[5],
        }
    except Exception as e:
        if logger:
            logger.error(f"Failed to read IDMC credentials for org '{org_name}': {str(e)}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def list_credentials(logger=None) -> List[Dict[str, str]]:
    """
    List all stored credential rows (passwords omitted).

    Args:
        logger: Optional logger instance

    Returns:
        List of dicts with orgName, entity, username, region, updatedAt.
        Passwords are intentionally excluded from the listing.
    """
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect()
        rows = conn.execute(
            "SELECT OrgName, Entity, Username, Region, UpdatedAt "
            "FROM Idmc_Credentials ORDER BY OrgName"
        ).fetchall()
        return [
            {
                'orgName': r[0],
                'entity': r[1],
                'username': r[2],
                'region': r[3],
                'updatedAt': r[4],
            }
            for r in rows
        ]
    except Exception as e:
        if logger:
            logger.error(f"Failed to list IDMC credentials: {str(e)}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def delete_credentials(org_name: str, logger=None) -> bool:
    """
    Delete the credentials row for an org.

    Args:
        org_name: IDMC organization name
        logger: Optional logger instance

    Returns:
        True if a row was deleted, False otherwise.
    """
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = _connect()
        cur = conn.execute("DELETE FROM Idmc_Credentials WHERE OrgName = ?", (org_name,))
        conn.commit()
        deleted = cur.rowcount > 0
        if logger:
            if deleted:
                logger.info(f"Deleted IDMC credentials for org '{org_name}'")
            else:
                logger.warning(f"No IDMC credentials found to delete for org '{org_name}'")
        return deleted
    except Exception as e:
        if logger:
            logger.error(f"Failed to delete IDMC credentials for org '{org_name}': {str(e)}")
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
