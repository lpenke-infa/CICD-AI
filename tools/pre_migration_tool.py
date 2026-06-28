"""
Pre-Migration Check Tool - Reusable module for pre-migration validation
"""

import logging
from typing import Optional, Callable, Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def pre_migration_check_tool(config_file_path: str) -> str:
    r"""
    Pre-Migration Check Tool.

    Validates source IICS assets before migration and generates a comprehensive Excel report.

    Checks:
    - Checked out assets
    - Invalid assets
    - Connection status in target
    - Migration statistics

    Args:
        config_file_path: Path to the JSON configuration file containing validation settings.
                         Default directory: Configs/ (relative to project root)

    The configuration file must contain:
        - IICS_SRC_username: Source environment username
        - IICS_SRC_password: Source environment password
        - IICS_SRC_region: Source region (e.g., dm-us)
        - IICS_TGT_username: Target environment username
        - IICS_TGT_password: Target environment password
        - IICS_TGT_region: Target region
        - PreMigration_Tag: List of tags to check (e.g., ["PreMigration", "ReadyToMigrate"])
        - ProjectName: Project name to validate (string or array)

    Optional fields (will use defaults if not provided):
        - logFileDir: Directory for logs (default: "Logs")
        - file_dir: Directory for reports (default: "Reports")
        - file_name: Report filename (default: "pre_migration_check.xlsx")

    Returns:
        Status message indicating validation will be executed with real-time updates

    IMPORTANT - SLACK FORMATTING:
    When responding to users about this tool, use Slack formatting (NOT Markdown):
    - Use *text* for bold (single asterisk, NOT **text**)
    - Use _text_ for italic
    - Use `code` for inline code
    - Use :emoji_name: for emojis
    """
    return "Pre-migration check will be executed with real-time updates"


def execute_pre_migration_check(
    config_file_path: str,
    say_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Execute the actual pre-migration validation with step-by-step updates.

    This function is called separately from the tool definition to allow
    real-time progress updates via the say_callback.

    Args:
        config_file_path: Path to the JSON configuration file
        say_callback: Optional callback function for real-time Slack updates

    Returns:
        Dictionary containing:
            - success (bool): Whether validation succeeded
            - message (str): Summary message
            - asset_count (int): Number of assets found
            - checked_out_count (int): Number of checked-out assets
            - invalid_count (int): Number of invalid assets
            - connection_count (int): Number of connections checked
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

        # Load configuration to show preview
        import json
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Show configuration preview
        if say_callback:
            config_preview = f"""📋 *Pre-Migration Check Configuration:*

🎯 *Source Environment:*
   • Username: `{config['IICS_SRC_username']}`
   • Password: `{'*' * 8}`
   • Region: `{config['IICS_SRC_region']}`

🎯 *Target Environment:*
   • Username: `{config['IICS_TGT_username']}`
   • Password: `{'*' * 8}`
   • Region: `{config['IICS_TGT_region']}`

📦 *Validation Details:*
   • Project: `{config.get('ProjectName', 'N/A')}`
   • Tags to Check: `{', '.join(config.get('PreMigration_Tag', []))}`

Proceeding with validation..."""
            say_callback(config_preview)

        if say_callback:
            say_callback("🔍 Starting Pre-Migration Check...")

        # Import the new PreMigrationCheck main module
        from PreMigrationCheck.main import run_pre_migration_check

        # Execute the check with real-time callback
        result = run_pre_migration_check(config_file_path, say_callback=say_callback)

        if not result['success']:
            if say_callback:
                say_callback(f"⚠️  {result['message']}")
            return result

        # Main module already sent all updates via callback, just return result

        return result

    except Exception as e:
        error_msg = f"❌ *Pre-Migration Check Failed:* {str(e)}"
        logger.error(f"Pre-migration check error: {str(e)}", exc_info=True)
        if say_callback:
            say_callback(error_msg)
        return {
            "success": False,
            "message": str(e),
            "asset_count": 0,
            "checked_out_count": 0,
            "invalid_count": 0,
            "connection_count": 0,
            "report_path": None
        }
