"""
Post-Migration Validation Main Module
Validates migrated assets and generates Excel report
"""
import json
import sys
import os
import logging
from datetime import datetime

# Handle both direct execution and package import
try:
    from . import login
    from . import utility
    from . import migration_statistics
    from . import tag_handling
except ImportError:
    import login
    import utility
    import migration_statistics
    import tag_handling


def create_logger(log_dir: str) -> logging.Logger:
    """
    Create and configure logger

    Args:
        log_dir: Directory for log files

    Returns:
        Configured logger instance
    """
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("PostMigrationCheck")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Clear existing handlers
    logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
    )

    # File handler with append mode
    log_file = os.path.join(log_dir, 'PostMigrationCheck.log')
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # Log session separator
    logger.info("="*80)
    logger.info(f"Post-Migration Check Session Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)

    return logger


def run_post_migration_check(config_path: str) -> dict:
    """
    Run post-migration validation

    Args:
        config_path: Path to configuration JSON file

    Returns:
        Dictionary with validation results

    Raises:
        Exception: If validation fails
    """
    # Load configuration
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Support flexible field names
    # Log directory is static ('Logs'); ignore any custom value in the config
    # and never require it to be present.
    _custom_log_dir = config.get('logFileDir') or config.get('file_dir')
    logger = create_logger('Logs')
    if _custom_log_dir and _custom_log_dir != 'Logs':
        logger.warning(f"Custom log directory '{_custom_log_dir}' ignored; using standard 'Logs' directory")

    # Handle ProjectName - could be string or array (from CICD config)
    project_name = config.get('ProjectName')
    if isinstance(project_name, list):
        project_name = project_name[0]
    config['ProjectName'] = project_name
    logger.info("=" * 80)
    logger.info("Post-Migration Validation Started")
    logger.info("=" * 80)

    try:
        # Login to target environment
        logger.info("Logging into target IICS environment")
        login_data = login.login(
            config['IICS_TGT_username'],
            config['IICS_TGT_password'],
            config['IICS_TGT_region'],
            logger
        )

        server_url = login_data['baseApiUrl']
        session_id = login_data['sessionId']

        # Get assets by tags
        logger.info(f"Retrieving assets with tags: {config['PostMigration_Tag']}")
        assets = tag_handling.get_assets_by_tags(
            session_id,
            server_url,
            config['PostMigration_Tag'],
            logger
        )

        if not assets:
            logger.warning("No assets found with specified tags")
            return {
                "success": False,
                "message": "No assets found with specified tags",
                "asset_count": 0
            }

        # The tag query returns every tagged asset across ALL projects. Filter to
        # the target project here so the reported asset count matches the report
        # (statistics also filter by project).
        all_tagged_count = len(assets)
        assets = [
            asset for asset in assets
            if (asset.get('path') or '').startswith(f"{project_name}/")
        ]
        skipped_count = all_tagged_count - len(assets)
        logger.info(
            f"Tagged assets: {all_tagged_count} total, "
            f"{len(assets)} in project '{project_name}', {skipped_count} in other projects"
        )

        if not assets:
            msg = (
                f"No tagged assets belong to project '{project_name}' "
                f"({all_tagged_count} tagged asset(s) found in other projects)"
            )
            logger.warning(msg)
            return {
                "success": False,
                "message": msg,
                "asset_count": 0
            }

        # Generate statistics
        logger.info("Generating migration statistics")
        stats = migration_statistics.generate_migration_statistics(
            assets,
            config['ProjectName'],
            logger
        )

        # Write Excel report
        sheet_data = {
            'MigrationStat': stats if stats else []
        }

        # Reports directory is static ('Reports'); ignore any custom value.
        if config.get('reportFileDir') and config['reportFileDir'] != 'Reports':
            logger.warning(f"Custom reportFileDir '{config['reportFileDir']}' ignored; using standard 'Reports' directory")
        report_dir = 'Reports'

        # Generate timestamped report filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"PostMigrationReport_{timestamp}.xlsx"

        report_path = utility.write_excel_report(
            logger,
            report_dir,
            report_filename,
            sheet_data
        )

        logger.info("=" * 80)
        logger.info("Post-Migration Validation Completed Successfully")
        logger.info(f"Report generated: {report_path}")
        logger.info(f"Total assets validated: {len(assets)}")
        logger.info(f"Session Ended - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        return {
            "success": True,
            "message": "Validation completed successfully",
            "asset_count": len(assets),
            "report_path": report_path
        }

    except Exception as e:
        logger.error(f"Post-migration validation failed: {str(e)}", exc_info=True)
        logger.info(f"Session Ended with Error - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        raise


def main():
    """Command-line entry point"""
    if len(sys.argv) != 2:
        print("Usage: python Main.py <path_to_config.json>")
        sys.exit(1)

    try:
        config_path = sys.argv[1]
        result = run_post_migration_check(config_path)

        if result['success']:
            print(f"\nValidation completed successfully")
            print(f"Assets validated: {result['asset_count']}")
            print(f"Report: {result['report_path']}")
            return 0
        else:
            print(f"\n{result['message']}")
            return 1

    except Exception as e:
        print(f"\nValidation failed: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

