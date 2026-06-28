"""
CICD Migration Tool - Reusable module for CI/CD operations
"""

import logging
from typing import Optional, Callable, Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def cicd_migration_tool(config_file_path: str) -> str:
    r"""
    CI/CD Migration & Deployment Tool.

    Migrates IICS assets from source to target environment using Git-based version control.

    Args:
        config_file_path: Path to the JSON configuration file containing migration settings.
                         Default directory: Configs/ (relative to project root)

    The configuration file must contain:
        - ProjectName: IICS project name
        - IICS_SRC_username, IICS_SRC_password, IICS_SRC_region: Source credentials
        - IICS_TGT_username, IICS_TGT_password, IICS_TGT_region: Target credentials
        - PreMigration_Tag: Tags to filter source assets
        - PostMigration_Tag: Tags to apply to migrated assets
        - Git configuration: repository URL, branches, credentials
        - logFileDir: Directory for log files

    Returns:
        Status message indicating the migration will be executed with real-time updates

    IMPORTANT - SLACK FORMATTING:
    When responding to users about this tool, use Slack formatting (NOT Markdown):
    - Use *text* for bold (single asterisk, NOT **text**)
    - Use _text_ for italic
    - Use `code` for inline code
    - Use :emoji_name: for emojis
    """
    return "Migration will be executed with real-time updates"


def execute_cicd_migration(
    config_file_path: str,
    say_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Execute the actual CICD migration with step-by-step updates.

    This function is called separately from the tool definition to allow
    real-time progress updates via the say_callback.

    Args:
        config_file_path: Path to the JSON configuration file
        say_callback: Optional callback function for real-time Slack updates

    Returns:
        Dictionary containing:
            - success (bool): Whether migration succeeded
            - message (str): Summary message
            - config_path (str): Path to config file used
            - migration_completed (bool): Migration completion status
            - post_migration_tag (list): Tags applied
            - project_name (str): Project name
            - target_username (str): Target environment username
            - target_password (str): Target environment password
            - target_region (str): Target environment region
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

        from CICDMigration.logger import create_logger
        from CICDMigration.login import iics_login
        from CICDMigration.taggedAssets import tagged_assets
        from CICDMigration.cherrypick import cherrypick
        from CICDMigration.createProjectsAndFolders import create_projects_and_folders
        from CICDMigration.pull import pull_assets
        from CICDMigration.postMigrationTag import post_migration_tag
        from CICDMigration.database import add_record
        from CICDMigration.utils import validate_input_data
        from CICDMigration.main import load_configuration

        # Load and validate configuration
        input_data = load_configuration(config_file_path)
        logger_instance = create_logger(input_data['logFileDir'])
        validate_input_data(input_data, logger_instance)

        # Show configuration preview
        if say_callback:
            config_preview = f"""📋 *CI/CD Migration Configuration:*

🎯 *Source Environment:*
   • Username: `{input_data['IICS_SRC_username']}`
   • Password: `{'*' * 8}`
   • Region: `{input_data['IICS_SRC_region']}`

🎯 *Target Environment:*
   • Username: `{input_data['IICS_TGT_username']}`
   • Password: `{'*' * 8}`
   • Region: `{input_data['IICS_TGT_region']}`

📦 *Migration Details:*
   • Project: `{input_data['ProjectName'][0]}`
   • Pre-Migration Tags: `{', '.join(input_data['PreMigration_Tag'])}`
   • Post-Migration Tags: `{', '.join(input_data['PostMigration_Tag'])}`

🌿 *Git Configuration:*
   • Repository: `{input_data['Git_Repository_URL']}`
   • Source Branch: `{input_data['Git_SRC_Branch']}`
   • Target Branch: `{input_data['Git_TGT_Branch']}`

Proceeding with migration..."""
            say_callback(config_preview)

        if say_callback:
            say_callback("🚀 Starting CI/CD Migration Process...\n" + "=" * 50)

        # Step 1: Authenticate to Source IICS
        if say_callback:
            say_callback("🔐 *STEP 1/8:* Authenticating to Source IICS...")

        src_data = iics_login(
            input_data['IICS_SRC_username'],
            input_data['IICS_SRC_password'],
            input_data['IICS_SRC_region'],
            logger_instance
        )

        if say_callback:
            say_callback(f"✅ Logged into Source Org: *{src_data['orgName']}*")

        # Step 2: Retrieve Tagged Assets
        if say_callback:
            say_callback("🏷️  *STEP 2/8:* Retrieving Tagged Assets from Source...")

        git_paths, asset_metadata = tagged_assets(
            src_data,
            input_data['PreMigration_Tag'],
            input_data['ProjectName'][0],
            logger_instance
        )

        if not asset_metadata:
            raise Exception("No assets found with specified tags")

        if say_callback:
            say_callback(f"✅ Found *{len(asset_metadata)}* assets to migrate")

        # Step 3: Authenticate to Target IICS
        if say_callback:
            say_callback("🔐 *STEP 3/8:* Authenticating to Target IICS...")

        tgt_data = iics_login(
            input_data['IICS_TGT_username'],
            input_data['IICS_TGT_password'],
            input_data['IICS_TGT_region'],
            logger_instance
        )

        if say_callback:
            say_callback(f"✅ Logged into Target Org: *{tgt_data['orgName']}*")

        # Step 4: Create Projects and Folders
        if say_callback:
            say_callback("📁 *STEP 4/8:* Creating Required Projects and Folders...")

        create_projects_and_folders(
            asset_metadata,
            tgt_data['sessionId'],
            tgt_data['baseApiUrl'],
            logger_instance
        )

        if say_callback:
            say_callback("✅ Projects and folders verified/created successfully")

        # Step 5: Git Cherry-pick
        if say_callback:
            say_callback("🌿 *STEP 5/8:* Cherry-picking Assets via Git...")

        commit_hash = cherrypick(input_data, git_paths, logger_instance)

        if say_callback:
            say_callback(f"✅ Git operations complete. Commit: `{commit_hash[:8]}`")

        # Step 6: Pull Assets to Target
        if say_callback:
            say_callback("⬇️  *STEP 6/8:* Pulling Assets to Target Environment...")

        pull_assets(asset_metadata, commit_hash, tgt_data, logger_instance)

        if say_callback:
            say_callback(f"✅ Assets pulled successfully to *{tgt_data['orgName']}*")

        # Step 7: Apply Post-Migration Tags
        if say_callback:
            say_callback("🏷️  *STEP 7/8:* Applying Post-Migration Tags...")

        post_migration_tag(
            asset_metadata,
            tgt_data,
            input_data["PostMigration_Tag"],
            logger_instance
        )

        if say_callback:
            say_callback(f"✅ Tagged *{len(asset_metadata)}* assets with *{input_data['PostMigration_Tag'][0]}*")

        # Step 8: Record in Database
        if say_callback:
            say_callback("💾 *STEP 8/8:* Recording Migration in Database...")

        try:
            add_record(
                input_data['ProjectName'][0],
                src_data['orgName'],
                src_data['orgId'],
                commit_hash,
                input_data['PostMigration_Tag'][0],
                tgt_data['orgId'],
                tgt_data['orgName'],
                len(asset_metadata),
                logger_instance
            )
            if say_callback:
                say_callback("✅ Database record created")
        except Exception as e:
            logger_instance.warning(f"Database recording failed: {str(e)}")
            if say_callback:
                say_callback("⚠️  Database recording skipped (migration still successful)")

        # Final Summary
        final_message = f"""{"=" * 50}
🎉 *MIGRATION COMPLETED SUCCESSFULLY!*
{"=" * 50}

📊 *Summary:*
   • Assets Migrated: *{len(asset_metadata)}*
   • Source Org: *{src_data['orgName']}*
   • Target Org: *{tgt_data['orgName']}*
   • Commit Hash: `{commit_hash}`

{"=" * 50}

Would you like to run *Post-Migration Validation* to verify the migrated assets?
Reply with "*yes*" to proceed."""

        if say_callback:
            say_callback(final_message)

        return {
            "success": True,
            "message": "Migration completed successfully",
            "config_path": config_file_path,
            "migration_completed": True,
            "post_migration_tag": input_data.get("PostMigration_Tag", []),
            "project_name": input_data['ProjectName'][0],
            "target_username": input_data['IICS_TGT_username'],
            "target_password": input_data['IICS_TGT_password'],
            "target_region": input_data['IICS_TGT_region']
        }

    except Exception as e:
        error_msg = f"❌ *Migration Failed:* {str(e)}"
        logger.error(f"Migration error: {str(e)}", exc_info=True)
        if say_callback:
            say_callback(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "config_path": config_file_path
        }
