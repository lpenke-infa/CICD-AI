"""
Database operations for IICS CI/CD automation
"""
import datetime
import pymssql
from typing import Optional


SERVER = ''
DATABASE = ''
DB_USER = r''
DB_PASSWORD = r''


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
    Add deployment record to database using parameterized query

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
        True if successful, False otherwise
    """
    conn: Optional[pymssql.Connection] = None
    cursor: Optional[pymssql.Cursor] = None

    try:
        today = datetime.date.today()

        conn = pymssql.connect(
            host=SERVER,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DATABASE
        )

        cursor = conn.cursor()

        query = """
            INSERT INTO dbo.Deployment_Details
            (ProjectName, IICSSourceOrg, IICSSourceOrgID, CommitHash, Tag,
             Deployment_Date, Rollback_Date, IICSTargetOrgID, IICSTargetOrg, AssetsMigrated)
            VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s, %d)
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
        logger.info('Record inserted into Database successfully')
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
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                logger.error(f"Error closing cursor: {str(e)}")
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")

