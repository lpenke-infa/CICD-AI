"""
Database operations for IICS CI/CD automation.

Uses SQLite (a single local file, no server required) to record one row per
migration. The database file lives in the project's 'Database' folder by
default; the full path can be overridden with the DB_PATH environment variable.
"""
import os
import sqlite3
import datetime
from typing import Optional


# Path to the SQLite database file. Defaults to 'Database/deployments.db' in the
# project root (two levels up from this file: CICDMigration/ -> project root).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv('DB_PATH', os.path.join(_PROJECT_ROOT, 'Database', 'deployments.db'))


# Table schema. Created automatically on first use if it does not exist.
_CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS Deployment_Details (
        Id              INTEGER PRIMARY KEY AUTOINCREMENT,
        ProjectName     TEXT    NOT NULL,
        IICSSourceOrg   TEXT,
        IICSSourceOrgID TEXT,
        CommitHash      TEXT,
        Tag             TEXT,
        Deployment_Date TEXT    NOT NULL,
        Rollback_Date   TEXT,
        IICSTargetOrgID TEXT,
        IICSTargetOrg   TEXT,
        AssetsMigrated  INTEGER
    )
"""


def add_record(
    project_name: str,
    iics_source_org: str,
    iics_source_org_id: str,
    commit_hash: str,
    tag: str,
    iics_target_org_id: str,
    iics_target_org: str,
    assets_migrated: int,
    logger
) -> bool:
    """
    Add a deployment record to the SQLite database using a parameterized query.

    The table is created automatically if it does not exist. This function never
    raises: on any failure it logs the error and returns False, so a database
    problem cannot abort a successful migration.

    Args:
        project_name: Name of the project
        iics_source_org: Source IICS organization name
        iics_source_org_id: Source IICS organization ID
        commit_hash: Git commit hash
        tag: Migration tag
        iics_target_org_id: Target IICS organization ID
        iics_target_org: Target IICS organization name
        assets_migrated: Number of assets migrated
        logger: Logger instance

    Returns:
        True if the record was inserted, False otherwise.
    """
    conn: Optional[sqlite3.Connection] = None

    try:
        today = datetime.date.today().isoformat()

        # Ensure the parent directory (e.g. Database/) exists before connecting
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Ensure the table exists before inserting
        cursor.execute(_CREATE_TABLE_SQL)

        query = """
            INSERT INTO Deployment_Details
            (ProjectName, IICSSourceOrg, IICSSourceOrgID, CommitHash, Tag,
             Deployment_Date, Rollback_Date, IICSTargetOrgID, IICSTargetOrg, AssetsMigrated)
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
        """

        cursor.execute(
            query,
            (
                project_name,
                iics_source_org,
                iics_source_org_id,
                commit_hash,
                tag,
                today,
                iics_target_org_id,
                iics_target_org,
                assets_migrated
            )
        )

        conn.commit()
        logger.info(f"Record inserted into database successfully: {DB_PATH}")
        return True

    except Exception as e:
        logger.critical(f"DB error: Unable to add record to DB - {str(e)}")
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.critical(f"Rollback failed: {str(rollback_error)}")
        return False

    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")
