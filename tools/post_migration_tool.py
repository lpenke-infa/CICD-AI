"""
Post-Migration Check Tool - Reusable module for validation operations
"""

import logging
import json
from typing import Optional, Callable, Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def post_migration_check_tool(config_file_path: str) -> str:
    r"""
    Post-Migration Validation Tool.

    Validates migrated IICS assets and generates an Excel report.
    Can be run independently or after a CI/CD migration.

    Args:
        config_file_path: Path to the JSON configuration file containing validation settings.
                         Default directory: Configs/ (relative to project root)

    The configuration file must contain:
        - IICS_TGT_username: Target environment username
        - IICS_TGT_password: Target environment password
        - IICS_TGT_region: Target region (e.g., dm-us)
        - PostMigration_Tag: List containing exactly one tag to check (e.g., ["Migrated"])
        - ProjectName: Project name to validate
        - logFileDir: Directory for logs (e.g., "Logs")
        - file_dir: Directory for report (e.g., "Reports")
        - file_name: Report filename (e.g., "validation_report.xlsx")

    Returns:
        Status message indicating validation will be executed with real-time updates

    IMPORTANT - SLACK FORMATTING:
    When responding to users about this tool, use Slack formatting (NOT Markdown):
    - Use *text* for bold (single asterisk, NOT **text**)
    - Use _text_ for italic
    - Use `code` for inline code
    - Use :emoji_name: for emojis
    """
    return "Post-migration check will be executed with real-time updates"


def execute_post_migration_check(
    config_file_path: str,
    say_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Execute the actual post-migration validation with step-by-step updates.

    This function is called separately from the tool definition to allow
    real-time progress updates via the say_callback.

    Args:
        config_file_path: Path to the JSON configuration file
        say_callback: Optional callback function for real-time Slack updates

    Returns:
        Dictionary containing:
            - success (bool): Whether validation succeeded
            - message (str): Summary message
            - asset_count (int): Number of assets validated
            - report_path (str): Path to generated Excel report
    """
    try:
        import os

        # If only filename provided, prepend Configs directory (relative to project root)
        if not os.path.isabs(config_file_path) and '\\' not in config_file_path and '/' not in config_file_path:
            # Get project root (parent of tools directory)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_file_path = os.path.join(project_root, "Configs", config_file_path)

        # Verify file exists
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f"Configuration file not found: {config_file_path}")

        if say_callback:
            say_callback("🔍 Starting Post-Migration Validation...")

        from PostMigrationCheck.login import login
        from PostMigrationCheck.tag_handling import get_assets_by_tags
        from PostMigrationCheck.migration_statistics import generate_migration_statistics
        from PostMigrationCheck.utility import write_excel_report
        from PostMigrationCheck.main import create_logger

        # Load configuration
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Log directory is static ('Logs'); ignore any custom value in the config.
        logger_instance = create_logger('Logs')
        if config.get('logFileDir') and config['logFileDir'] != 'Logs':
            logger_instance.warning(
                f"Custom logFileDir '{config['logFileDir']}' ignored; using standard 'Logs' directory"
            )

        # Normalize ProjectName (may be a string or an array from a CICD config)
        # so validation sees a string, matching how the flow uses it below.
        if isinstance(config.get('ProjectName'), list) and config['ProjectName']:
            config['ProjectName'] = config['ProjectName'][0]

        # Validate configuration before doing any work (fail fast with a clear
        # message instead of raising a raw KeyError deep in the flow)
        try:
            from common.config_validation import validate_config
            validation = validate_config(config, config_type='post')
            for warning in validation.get('warnings', []):
                logger_instance.warning(warning)
            config.update(validation['config'])
        except ValueError as e:
            logger_instance.error(f"Configuration validation failed: {str(e)}")
            if say_callback:
                say_callback(f"❌ *Configuration validation failed:*\n{str(e)}")
            return {
                "success": False,
                "message": str(e),
                "asset_count": 0,
                "report_path": None
            }

        # Step 1: Authenticate to Target IICS
        if say_callback:
            say_callback("🔐 *STEP 1/3:* Authenticating to Target IICS...")

        login_data = login(
            config['IICS_TGT_username'],
            config['IICS_TGT_password'],
            config['IICS_TGT_region'],
            logger_instance
        )

        server_url = login_data['baseApiUrl']
        session_id = login_data['sessionId']

        if say_callback:
            say_callback("✅ Logged into Target Org")

        # Step 2: Retrieve Assets by Tags
        if say_callback:
            say_callback("📋 *STEP 2/3:* Retrieving Migrated Assets...")

        assets = get_assets_by_tags(
            session_id,
            server_url,
            config['PostMigration_Tag'],
            logger_instance
        )

        if not assets:
            if say_callback:
                say_callback("⚠️  No assets found with specified tags")
            return {
                "success": False,
                "message": "No assets found with specified tags",
                "asset_count": 0,
                "report_path": None
            }

        # The tag query returns every tagged asset across ALL projects. Filter to
        # the target project here so the Slack count and the report both reflect
        # only assets in this project (the report's statistics filter by project).
        project_name = config['ProjectName']
        all_tagged_count = len(assets)
        assets = [
            asset for asset in assets
            if (asset.get('path') or '').startswith(f"{project_name}/")
        ]
        skipped_count = all_tagged_count - len(assets)
        logger_instance.info(
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
            logger_instance.warning(msg)
            return {
                "success": False,
                "message": msg,
                "asset_count": 0,
                "report_path": None
            }

        if say_callback:
            say_callback(f"✅ Found *{len(assets)}* migrated assets in project *{project_name}*")
            if skipped_count:
                say_callback(
                    f"ℹ️  {skipped_count} additional tagged asset(s) belong to other "
                    f"projects and were excluded."
                )

        # Step 3: Generate Validation Report
        if say_callback:
            say_callback("📊 *STEP 3/3:* Generating Validation Report...")

        stats = generate_migration_statistics(
            assets,
            config['ProjectName'],
            logger_instance
        )

        logger_instance.info(f"Statistics generated: {len(stats)} entries")
        if not stats:
            logger_instance.warning(f"No statistics matched project: {config['ProjectName']}")
            logger_instance.warning(f"Sample asset paths: {[a.get('path', 'N/A') for a in assets[:3]]}")

        sheet_data = {
            'MigrationStat': stats if stats else []
        }

        # Reports directory is static ('Reports'); ignore any custom value.
        from datetime import datetime
        if config.get('reportFileDir') and config['reportFileDir'] != 'Reports':
            logger_instance.warning(
                f"Custom reportFileDir '{config['reportFileDir']}' ignored; using standard 'Reports' directory"
            )
        report_dir = 'Reports'

        # Generate timestamped report filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"PostMigrationReport_{timestamp}.xlsx"

        report_path = write_excel_report(
            logger_instance,
            report_dir,
            report_filename,
            sheet_data
        )

        # Final Summary
        final_message = f"""{"=" * 50}
✅ *POST-MIGRATION VALIDATION COMPLETED!*
{"=" * 50}

📊 *Summary:*
   • Assets Validated: *{len(assets)}*
   • Project: *{config['ProjectName']}*
   • Tags Checked: *{', '.join(config['PostMigration_Tag'])}*

📄 *Report Generated:* `{report_path}`

{"=" * 50}"""

        if say_callback:
            say_callback(final_message)

        return {
            "success": True,
            "message": "Validation completed successfully",
            "asset_count": len(assets),
            "report_path": report_path
        }

    except Exception as e:
        error_msg = f"❌ *Post-Migration Validation Failed:* {str(e)}"
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        if say_callback:
            say_callback(error_msg)
        return {
            "success": False,
            "message": str(e),
            "asset_count": 0,
            "report_path": None
        }
