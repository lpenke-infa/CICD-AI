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

    # Log directory is static ('Logs'); ignore any custom value in the config
    # and never require it to be present.
    _custom_log_dir = config.get('logFileDir') or config.get('file_dir')
    logger = create_logger('Logs')
    if _custom_log_dir and _custom_log_dir != 'Logs':
        logger.warning(f"Custom log directory '{_custom_log_dir}' ignored; using standard 'Logs' directory")

    # Handle ProjectName - could be string or array (from CICD config)
    project_name = config.get('ProjectName')
    if isinstance(project_name, list):
        project_name = project_name[0]  # Take first project from array
    config['ProjectName'] = project_name
    logger.info("=" * 80)
    logger.info("Pre-Migration Check Started")
    logger.info("=" * 80)

    # Validate configuration before doing any work (fail fast with a clear message
    # instead of raising a raw KeyError deep in the flow)
    try:
        from common.config_validation import validate_config
        validation = validate_config(config, config_type='pre')
        for warning in validation.get('warnings', []):
            logger.warning(warning)
        config.update(validation['config'])
    except ValueError as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        if say_callback:
            say_callback(f"❌ *Configuration validation failed:*\n{str(e)}")
        return {
            "success": False,
            "message": str(e),
            "asset_count": 0,
            "checked_out_count": 0,
            "invalid_count": 0,
            "connection_count": 0,
            "report_path": None
        }

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

        # The tag query returns every tagged asset across ALL projects. Filter to
        # the target project here so every downstream count (Slack summary,
        # statistics, checked-out, connections) is consistent and matches the
        # migration flow, which also filters by project.
        project_name = config['ProjectName']
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
            if say_callback:
                say_callback(f"⚠️  {msg}")
            logger.warning(msg)
            return {
                "success": False,
                "message": msg,
                "asset_count": 0,
                "checked_out_count": 0,
                "invalid_count": 0,
                "connection_count": 0
            }

        logger.info(f"Found {len(assets)} assets in project '{project_name}'")

        if say_callback:
            say_callback(f"✅ Found *{len(assets)}* assets ready for migration in project *{project_name}*")
            if skipped_count:
                say_callback(
                    f"ℹ️  {skipped_count} additional tagged asset(s) belong to other "
                    f"projects and were excluded."
                )

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
            say_callback("📄 *Generating Report...*")
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

        # Reports directory is static ('Reports'); ignore any custom value.
        if config.get('reportFileDir') and config['reportFileDir'] != 'Reports':
            logger.warning(f"Custom reportFileDir '{config['reportFileDir']}' ignored; using standard 'Reports' directory")
        report_dir = 'Reports'

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

        # Flag blocking-class issues that can cause the migration to fail, so the
        # summary reflects their severity instead of a clean "completed" that
        # invites the user to proceed blindly:
        #   - invalid assets          -> likely fail to deploy
        #   - checked-out assets      -> uncommitted changes
        #   - missing target connections -> deployment WILL fail (asset depends
        #     on a connection that does not exist in the target org)
        invalid_count = len(invalid_assets)
        checked_out_count = len(checked_out_assets)
        missing_connections = [
            c.get('Connection Name', 'Unknown')
            for c in connection_status
            if str(c.get('Connection Status', '')).strip().lower() != 'available'
        ]
        missing_connection_count = len(missing_connections)
        has_issues = invalid_count > 0 or checked_out_count > 0 or missing_connection_count > 0

        if say_callback:
            # Per-line markers so issues stand out from clean counts.
            checked_out_line = (
                f"   • ⚠️ Checked-Out Assets: *{checked_out_count}*  _(uncommitted changes)_"
                if checked_out_count else f"   • Checked-Out Assets: {checked_out_count}"
            )
            invalid_line = (
                f"   • ⛔ Invalid Assets: *{invalid_count}*  _(likely to fail migration)_"
                if invalid_count else f"   • Invalid Assets: {invalid_count}"
            )
            connection_line = (
                f"   • ⛔ Connections Checked: *{len(connection_status)}* "
                f"({missing_connection_count} missing in target — _deployment will fail_)"
                if missing_connection_count else f"   • Connections Checked: {len(connection_status)}"
            )

            if has_issues:
                header = "⚠️ *PRE-MIGRATION CHECK COMPLETED — ISSUES FOUND*"
                reasons = []
                if missing_connection_count:
                    reasons.append(
                        f"*{missing_connection_count}* connection(s) missing in the target "
                        f"(`{', '.join(missing_connections)}`) — the deployment *will* fail until these exist"
                    )
                if invalid_count:
                    reasons.append(f"*{invalid_count}* invalid asset(s) likely to fail migration")
                if checked_out_count:
                    reasons.append(f"*{checked_out_count}* checked-out asset(s) with uncommitted changes")
                reason_text = "\n".join(f"   • {r}" for r in reasons)
                footer = f"""⚠️ *Review needed before migrating:*
{reason_text}

Please review the report above.
If you still want to migrate despite these issues, reply "*yes, proceed anyway*"."""
            else:
                header = "✅ *PRE-MIGRATION CHECK COMPLETED!*"
                footer = """Would you like to proceed with *CI/CD Migration*?
Reply with "*yes*" to proceed."""

            final_summary = f"""{"=" * 50}
{header}
{"=" * 50}

📊 *Summary:*
   • Assets Found: *{len(assets)}*
{checked_out_line}
{invalid_line}
{connection_line}

📄 *Report Generated:* `{report_path}`

{"=" * 50}

{footer}"""
            say_callback(final_summary)

        return {
            "success": True,
            "message": "Pre-migration check completed successfully",
            "asset_count": len(assets),
            "checked_out_count": checked_out_count,
            "invalid_count": invalid_count,
            "connection_count": len(connection_status),
            "missing_connection_count": missing_connection_count,
            "report_path": report_path,
            "has_issues": has_issues
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
