"""
Pre-Migration Check Main Module
Validates source assets before migration and generates comprehensive Excel report
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
    from . import asset_validation
    from . import connection_check
except ImportError:
    import login
    import utility
    import migration_statistics
    import tag_handling
    import asset_validation
    import connection_check


def create_logger(log_dir: str) -> logging.Logger:
    """
    Create and configure logger

    Args:
        log_dir: Directory for log files

    Returns:
        Configured logger instance
    """
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("PreMigrationCheck")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Clear existing handlers
    logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
    )

    # File handler with append mode
    log_file = os.path.join(log_dir, 'PreMigrationCheck.log')
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
    logger.info(f"Pre-Migration Check Session Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)

    return logger


def run_pre_migration_check(config_path: str, say_callback=None) -> dict:
    """
    Run pre-migration check

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

    # Support both file_dir and logFileDir for logs
    log_dir = config.get('logFileDir', config.get('file_dir', 'Logs'))
    logger = create_logger(log_dir)

    # Handle ProjectName - could be string or array (from CICD config)
    project_name = config.get('ProjectName')
    if isinstance(project_name, list):
        project_name = project_name[0]  # Take first project from array
    config['ProjectName'] = project_name
    logger.info("=" * 80)
    logger.info("Pre-Migration Check Started")
    logger.info("=" * 80)

    try:
        # Step 1: Login to source environment
        if say_callback:
            say_callback("🔐 *STEP 1/6:* Authenticating to Source IICS...")
        logger.info("Step 1/6: Logging into source IICS environment")
        src_login_data = login.login(
            config['IICS_SRC_username'],
            config['IICS_SRC_password'],
            config['IICS_SRC_region'],
            logger
        )

        src_server_url = src_login_data['baseApiUrl']
        src_session_id = src_login_data['sessionId']

        if say_callback:
            say_callback(f"✅ Logged into Source Org: *{src_login_data['orgName']}*")

        # Step 2: Get assets by tags
        if say_callback:
            say_callback("📋 *STEP 2/6:* Retrieving Assets with Pre-Migration Tags...")
        logger.info(f"Step 2/6: Retrieving assets with tags: {config['PreMigration_Tag']}")
        assets = tag_handling.get_assets_by_tags(
            src_session_id,
            src_server_url,
            config['PreMigration_Tag'],
            logger
        )

        if not assets:
            if say_callback:
                say_callback("⚠️  No assets found with specified pre-migration tags")
            logger.warning("No assets found with specified tags")
            return {
                "success": False,
                "message": "No assets found with specified tags",
                "asset_count": 0,
                "checked_out_count": 0,
                "invalid_count": 0,
                "connection_count": 0
            }

        logger.info(f"Found {len(assets)} assets")

        if say_callback:
            say_callback(f"✅ Found *{len(assets)}* assets ready for migration")

        # Step 3: Check for checked-out assets
        if say_callback:
            say_callback("🔍 *STEP 3/6:* Checking for Checked-Out Assets...")
        logger.info("Step 3/6: Checking for checked-out assets")
        checked_out_assets, checked_out_excel = asset_validation.get_checked_out_assets(
            src_session_id,
            src_server_url,
            assets,
            config['ProjectName'],
            logger
        )

        if say_callback:
            say_callback(f"✅ Checked-out assets: {len(checked_out_assets)}")

        # Step 4: Validate assets
        if say_callback:
            say_callback("✔️  *STEP 4/6:* Validating Assets...")
        logger.info("Step 4/6: Validating assets")
        invalid_assets = asset_validation.validate_assets(
            src_session_id,
            src_server_url,
            assets,
            config['ProjectName'],
            logger
        )

        if say_callback:
            say_callback(f"✅ Invalid assets: {len(invalid_assets)}")

        # Step 5: Generate statistics
        if say_callback:
            say_callback("📊 *STEP 5/6:* Generating Migration Statistics...")
        logger.info("Step 5/6: Generating migration statistics")
        stats = migration_statistics.generate_migration_statistics(
            assets,
            config['ProjectName'],
            logger
        )

        if say_callback:
            say_callback(f"✅ Statistics generated")

        # Step 6: Check connections in target
        if say_callback:
            say_callback("🔌 *STEP 6/6:* Checking Connection Status in Target...")
        logger.info("Step 6/6: Checking connection status in target environment")

        # Login to target environment
        tgt_login_data = login.login(
            config['IICS_TGT_username'],
            config['IICS_TGT_password'],
            config['IICS_TGT_region'],
            logger
        )

        tgt_server_url = tgt_login_data['baseApiUrl']
        tgt_session_id = tgt_login_data['sessionId']

        if say_callback:
            say_callback(f"✅ Logged into Target Org: *{tgt_login_data['orgName']}*")

        # Get connection dependencies
        connection_names = connection_check.get_connection_dependencies(
            src_session_id,
            src_server_url,
            assets,
            config['ProjectName'],
            logger
        )

        # Check connection status in target
        connection_status = connection_check.check_connection_status_in_target(
            tgt_session_id,
            tgt_server_url,
            connection_names,
            logger
        )

        if say_callback:
            say_callback(f"✅ Connection status checked: {len(connection_status)} connections")

        # Write Excel report
        if say_callback:
            say_callback("📄 **Generating Report...**")
        logger.info("Generating comprehensive Excel report")

        # Define header rows for empty sheets
        checked_out_header = {'Project': '', 'Folder': '', 'Asset': ''}
        invalid_header = {'Project Name': '', 'Asset': '', 'Asset Type': ''}
        connection_header = {'Connection Name': '', 'Connection Status': ''}
        stats_header = {'Project': '', 'Folder': '', 'Asset': '', 'AssetType': '', 'Tags': ''}

        sheet_data = {
            'CheckedOutAssets': checked_out_excel if checked_out_excel else [checked_out_header],
            'InvalidAssets': invalid_assets if invalid_assets else [invalid_header],
            'Connections': connection_status if connection_status else [connection_header],
            'MigrationStat': stats if stats else [stats_header]
        }

        # Reports directory - use reportFileDir if specified, otherwise default to 'Reports'
        report_dir = config.get('reportFileDir', 'Reports')

        # Generate timestamped report filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"PreMigrationReport_{timestamp}.xlsx"

        report_path = utility.write_excel_report(
            logger,
            report_dir,
            report_filename,
            sheet_data
        )

        logger.info("=" * 80)
        logger.info("Pre-Migration Check Completed Successfully")
        logger.info(f"Report generated: {report_path}")
        logger.info(f"Total assets found: {len(assets)}")
        logger.info(f"Checked-out assets: {len(checked_out_assets)}")
        logger.info(f"Invalid assets: {len(invalid_assets)}")
        logger.info(f"Connections checked: {len(connection_status)}")
        logger.info(f"Session Ended - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        if say_callback:
            final_summary = f"""{"=" * 50}
✅ *PRE-MIGRATION CHECK COMPLETED!*
{"=" * 50}

📊 *Summary:*
   • Assets Found: *{len(assets)}*
   • Checked-Out Assets: {len(checked_out_assets)}
   • Invalid Assets: {len(invalid_assets)}
   • Connections Checked: {len(connection_status)}

📄 *Report Generated:* `{report_path}`

{"=" * 50}

Would you like to proceed with *CI/CD Migration*?
Reply with "*yes*" to proceed."""
            say_callback(final_summary)

        return {
            "success": True,
            "message": "Pre-migration check completed successfully",
            "asset_count": len(assets),
            "checked_out_count": len(checked_out_assets),
            "invalid_count": len(invalid_assets),
            "connection_count": len(connection_status),
            "report_path": report_path
        }

    except Exception as e:
        logger.error(f"Pre-migration check failed: {str(e)}", exc_info=True)
        logger.info(f"Session Ended with Error - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        raise


def main():
    """Command-line entry point"""
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_config.json>")
        sys.exit(1)

    try:
        config_path = sys.argv[1]
        result = run_pre_migration_check(config_path)

        if result['success']:
            print(f"\nPre-migration check completed successfully")
            print(f"Assets found: {result['asset_count']}")
            print(f"Checked-out assets: {result['checked_out_count']}")
            print(f"Invalid assets: {result['invalid_count']}")
            print(f"Connections checked: {result['connection_count']}")
            print(f"Report: {result['report_path']}")
            return 0
        else:
            print(f"\n{result['message']}")
            return 1

    except Exception as e:
        print(f"\nPre-migration check failed: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
