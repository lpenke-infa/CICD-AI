"""
Migration Statistics Module
"""
import logging
from typing import List, Dict


def generate_migration_statistics(assets: List[Dict], project_name: str, logger: logging.Logger) -> List[Dict]:
    """
    Generate migration statistics from asset list

    Args:
        assets: List of asset dictionaries
        project_name: Project name to filter by (optional - if None, includes all)
        logger: Logger instance

    Returns:
        List of statistics dictionaries with project/folder/asset breakdown
    """
    logger.info(f"Generating statistics for project: {project_name}")

    statistics = []
    project_filter_applied = False

    for asset in assets:
        path = asset.get('path', '')
        if not path:
            # Assets without path - still include them
            stat_entry = {
                "Project": asset.get("projectName", "N/A"),
                "Folder": None,
                "Asset": asset.get("name", "Unknown"),
                "AssetType": asset.get("type", ""),
                "Tags": ", ".join(asset.get("tags", []))
            }
            statistics.append(stat_entry)
            continue

        path_parts = path.split('/')

        # Check if we should filter by project name
        should_include = True
        if project_name and len(path_parts) > 0:
            if path_parts[0] == project_name:
                project_filter_applied = True
            else:
                should_include = False

        if should_include:
            if len(path_parts) >= 3:
                # Project/Folder/Asset
                stat_entry = {
                    "Project": path_parts[0],
                    "Folder": path_parts[1],
                    "Asset": path_parts[2],
                    "AssetType": asset.get("type", ""),
                    "Tags": ", ".join(asset.get("tags", []))
                }
            elif len(path_parts) == 2:
                # Project/Asset (no folder)
                stat_entry = {
                    "Project": path_parts[0],
                    "Folder": None,
                    "Asset": path_parts[1],
                    "AssetType": asset.get("type", ""),
                    "Tags": ", ".join(asset.get("tags", []))
                }
            elif len(path_parts) == 1:
                # Just asset name
                stat_entry = {
                    "Project": "N/A",
                    "Folder": None,
                    "Asset": path_parts[0],
                    "AssetType": asset.get("type", ""),
                    "Tags": ", ".join(asset.get("tags", []))
                }
            else:
                continue

            statistics.append(stat_entry)

    if not statistics and len(assets) > 0:
        logger.warning(f"No statistics generated. Project filter: {project_name}, Assets found: {len(assets)}")
        logger.warning(f"Sample asset path: {assets[0].get('path', 'N/A')}")

    logger.info(f"Generated {len(statistics)} statistics entries")
    return statistics

