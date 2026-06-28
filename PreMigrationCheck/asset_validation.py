"""
Asset Validation Module for Pre-Migration Check
Checks for checked-out assets and invalid assets
"""
import requests
import logging
from typing import List, Dict, Tuple
from time import sleep


def get_checked_out_assets(session_id: str, base_api_url: str, assets: List[Dict],
                           project_name: str, logger: logging.Logger) -> Tuple[List[Dict], List[Dict]]:
    """
    Check which assets are checked out

    Args:
        session_id: IICS session ID
        base_api_url: Base API URL
        assets: List of asset dictionaries
        project_name: Project name to filter
        logger: Logger instance

    Returns:
        Tuple of (checked_out_list, asset_list_for_excel)
    """
    logger.info(f"Checking checkout status for {len(assets)} assets")

    checked_out_assets = []
    asset_list_excel = []

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'INFA-SESSION-ID': session_id,
    }

    for asset in assets:
        path = asset.get('path', '')

        # Filter by project
        if not path.startswith(f"{project_name}/"):
            continue

        asset_id = asset.get('id')
        if not asset_id:
            continue

        # Check if asset is checked out
        try:
            url = f"{base_api_url}/public/core/v3/objects/{asset_id}"

            try:
                response = requests.get(url, headers=headers, timeout=30)

                # Skip 404s - asset might not support individual lookup
                if response.status_code == 404:
                    logger.debug(f"Asset {asset.get('name')} - 404 (skipping, might be system object)")
                    continue

                response.raise_for_status()
                asset_details = response.json()

                # Check checkout status
                is_checked_out = asset_details.get('checkedOut', False)

                if is_checked_out:
                    checked_out_assets.append(asset)

                    # Parse path for Excel report
                    path_parts = path.split('/')
                    excel_entry = {
                        'Project': path_parts[0] if len(path_parts) > 0 else 'N/A',
                        'Folder': path_parts[1] if len(path_parts) > 1 else 'N/A',
                        'Asset': asset.get('name', 'Unknown')
                    }
                    asset_list_excel.append(excel_entry)

                    logger.debug(f"Checked out asset: {asset.get('name')}")

            except requests.exceptions.RequestException as e:
                # Log and continue with next asset
                logger.debug(f"Could not check asset {asset.get('name')}: {str(e)}")

        except Exception as e:
            logger.error(f"Error checking asset {asset.get('name')}: {str(e)}")
            continue

    logger.info(f"Found {len(checked_out_assets)} checked-out assets")
    return checked_out_assets, asset_list_excel


def validate_assets(session_id: str, base_api_url: str, assets: List[Dict],
                    project_name: str, logger: logging.Logger) -> List[Dict]:
    """
    Validate assets for common issues

    Args:
        session_id: IICS session ID
        base_api_url: Base API URL
        assets: List of asset dictionaries
        project_name: Project name to filter
        logger: Logger instance

    Returns:
        List of invalid asset dictionaries
    """
    logger.info(f"Validating {len(assets)} assets")

    invalid_assets = []

    # Common validation rules
    INVALID_ASSET_TYPES = ['OBSOLETE', 'DEPRECATED']

    for asset in assets:
        path = asset.get('path', '')

        # Filter by project
        if not path.startswith(f"{project_name}/"):
            continue

        asset_type = asset.get('type', '')
        asset_name = asset.get('name', 'Unknown')

        # Check for invalid asset types
        if asset_type in INVALID_ASSET_TYPES:
            path_parts = path.split('/')
            invalid_entry = {
                'Project Name': path_parts[0] if len(path_parts) > 0 else 'N/A',
                'Asset': asset_name,
                'Asset Type': asset_type
            }
            invalid_assets.append(invalid_entry)
            logger.debug(f"Invalid asset type: {asset_name} ({asset_type})")

        # Check for missing required fields
        if not asset.get('id'):
            path_parts = path.split('/')
            invalid_entry = {
                'Project Name': path_parts[0] if len(path_parts) > 0 else 'N/A',
                'Asset': asset_name,
                'Asset Type': 'MISSING_ID'
            }
            invalid_assets.append(invalid_entry)
            logger.debug(f"Asset missing ID: {asset_name}")

    logger.info(f"Found {len(invalid_assets)} invalid assets")
    return invalid_assets
