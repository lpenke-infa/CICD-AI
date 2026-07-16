"""
Main module for IICS CI/CD automation
Orchestrates the migration of tagged assets between IICS environments
"""
import sys
import json
import traceback
from typing import Dict
from datetime import datetime

from .logger import create_logger
from .login import login
from .taggedAssets import tagged_assets
from .cherrypick import cherrypick
from .createProjectsAndFolders import create_projects_and_folders
from .pull import pull_assets
from .postMigrationTag import post_migration_tag
from .database import add_record
from .utils import validate_input_data


def load_configuration(config_path: str) -> Dict:
    """
    Load and parse configuration file

    Args:
        config_path: Path to configuration JSON file

    Returns:
        Configuration dictionary

    Raises:
        Exception: If file cannot be loaded or parsed
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
        return config
    except FileNotFoundError:
        raise Exception(f"Configuration file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in configuration file: {str(e)}")
    except Exception as e:
        raise Exception(f"Error loading configuration: {str(e)}")


def run_migration(config_path: str) -> Dict:
    """
    Run migration workflow with given config path

    Args:
        config_path: Path to configuration JSON file

    Returns:
        Dictionary with migration results

    Raises:
        Exception: If migration fails
    """
    logger = None

    try:
        input_data = load_configuration(config_path)

        # Log directory is static ('Logs'); always use it, ignoring/​warning on
        # any custom value, and never require it to be present in the config.
        logger = create_logger('Logs')
        if input_data.get('logFileDir') and input_data['logFileDir'] != 'Logs':
            logger.warning(
                f"Custom logFileDir '{input_data['logFileDir']}' ignored; using standard 'Logs' directory"
            )
        input_data['logFileDir'] = 'Logs'
        logger.info("=" * 80)
        logger.info("IICS CI/CD Migration Process Started")
        logger.info("=" * 80)

        validate_input_data(input_data, logger)

        logger.info("Step 1: Authenticating to Source IICS Organization")
        src_data = login(
            input_data['IICS_SRC_username'],
            input_data['IICS_SRC_password'],
            input_data['IICS_SRC_region'],
            logger
        )
        logger.info(f"Successfully logged into Source Org: {src_data['orgName']}")

        logger.info("Step 2: Retrieving Tagged Assets from Source")
        git_paths, asset_metadata = tagged_assets(
            src_data,
            input_data['PreMigration_Tag'],
            input_data['ProjectName'],
            logger
        )

        if not asset_metadata:
            error_msg = "No assets found with specified tags"
            logger.error(error_msg)
            raise Exception(error_msg)

        logger.info(f"Found {len(asset_metadata)} assets to migrate")

        logger.info("Step 3: Authenticating to Target IICS Organization")
        tgt_data = login(
            input_data['IICS_TGT_username'],
            input_data['IICS_TGT_password'],
            input_data['IICS_TGT_region'],
            logger
        )
        logger.info(f"Successfully logged into Target Org: {tgt_data['orgName']}")

        logger.info("Step 4: Creating Required Projects and Folders in Target")
        create_projects_and_folders(
            asset_metadata,
            tgt_data['sessionId'],
            tgt_data['baseApiUrl'],
            logger
        )

        logger.info("Step 5: Cherry-picking Assets via Git")
        commit_hash = cherrypick(input_data, git_paths, logger)
        logger.info(f"Git operations completed. Commit: {commit_hash}")

        logger.info("Step 6: Pulling Assets to Target Environment")
        pull_assets(
            asset_metadata,
            commit_hash,
            tgt_data,
            logger
        )

        logger.info("Step 7: Applying Post-Migration Tags")
        post_migration_tag(
            asset_metadata,
            tgt_data,
            input_data["PostMigration_Tag"],
            logger
        )

        logger.info("Step 8: Recording Migration in Database")
        try:
            db_success = add_record(
                input_data['ProjectName'],
                src_data['orgName'],
                src_data['orgId'],
                commit_hash,
                input_data['PostMigration_Tag'][0],
                tgt_data['orgId'],
                tgt_data['orgName'],
                len(asset_metadata),
                logger
            )

            if not db_success:
                logger.warning("Database recording failed, but migration completed successfully")
        except Exception as e:
            logger.warning(f"Database recording failed: {str(e)}. Migration completed successfully.")

        logger.info("=" * 80)
        logger.info("MIGRATION COMPLETED SUCCESSFULLY")
        logger.info(f"Total Assets Migrated: {len(asset_metadata)}")
        logger.info(f"Source Org: {src_data['orgName']}")
        logger.info(f"Target Org: {tgt_data['orgName']}")
        logger.info(f"Commit Hash: {commit_hash}")
        logger.info(f"Session Ended - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        return {
            "success": True,
            "message": "Migration completed successfully",
            "assets_migrated": len(asset_metadata),
            "source_org": src_data['orgName'],
            "target_org": tgt_data['orgName'],
            "commit_hash": commit_hash
        }

    except Exception as e:
        if logger:
            logger.critical(f"Migration failed: {str(e)}")
            logger.critical(traceback.format_exc())
            logger.info(f"Session Ended with Error - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)
        else:
            print(f"ERROR: {str(e)}")
            print(traceback.format_exc())
        raise


def main():
    """
    Command-line entry point for migration
    """
    try:
        if len(sys.argv) != 2:
            print("Usage: python main.py <path_to_config.json>")
            sys.exit(1)

        config_path = sys.argv[1]
        result = run_migration(config_path)
        print(f"\n✅ {result['message']}")
        print(f"📊 Assets Migrated: {result['assets_migrated']}")
        print(f"🔄 Source: {result['source_org']} → Target: {result['target_org']}")
        return 0

    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
