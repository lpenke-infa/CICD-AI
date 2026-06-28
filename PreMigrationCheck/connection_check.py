"""
Connection Status Check Module for Pre-Migration Check
"""
import requests
import logging
from typing import List, Dict
from time import sleep


def get_connection_dependencies(session_id: str, base_api_url: str, assets: List[Dict],
                                project_name: str, logger: logging.Logger) -> List[str]:
    """
    Extract connection names from assets

    Args:
        session_id: IICS session ID
        base_api_url: Base API URL
        assets: List of asset dictionaries
        project_name: Project name to filter
        logger: Logger instance

    Returns:
        List of unique connection names
    """
    logger.info(f"Extracting connection dependencies from {len(assets)} assets")

    connection_names = set()
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

        # Get asset details to find connections
        try:
            url = f"{base_api_url}/public/core/v3/objects/{asset_id}"

            response = requests.get(url, headers=headers, timeout=30)

            # Skip 404s - asset might not support individual lookup
            if response.status_code == 404:
                logger.debug(f"Asset {asset.get('name')} - 404 (skipping)")
                continue

            response.raise_for_status()
            asset_details = response.json()

            # Extract connections from asset metadata
            # Note: Connection extraction logic depends on asset type
            # This is a simplified version
            metadata = asset_details.get('metadata', {})

            # Look for connection references in various fields
            if 'connections' in metadata:
                for conn in metadata['connections']:
                    if isinstance(conn, dict):
                        conn_name = conn.get('name')
                        if conn_name:
                            connection_names.add(conn_name)
                    elif isinstance(conn, str):
                        connection_names.add(conn)

        except requests.exceptions.RequestException as e:
            logger.debug(f"Could not get details for asset {asset.get('name')}: {str(e)}")
        except Exception as e:
            logger.debug(f"Error extracting connections from {asset.get('name')}: {str(e)}")

    logger.info(f"Found {len(connection_names)} unique connection dependencies")
    return list(connection_names)


def check_connection_status_in_target(session_id: str, base_api_url: str,
                                      connection_names: List[str], logger: logging.Logger) -> List[Dict]:
    """
    Check if connections exist in target environment

    Args:
        session_id: Target IICS session ID
        base_api_url: Target base API URL
        connection_names: List of connection names to check
        logger: Logger instance

    Returns:
        List of connection status dictionaries
    """
    logger.info(f"Checking status of {len(connection_names)} connections in target")

    connection_status_list = []
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'INFA-SESSION-ID': session_id,
    }

    for conn_name in connection_names:
        try:
            # Search for connection by name
            url = f"{base_api_url}/public/core/v3/objects?q=type=='CONNECTION' and name=='{conn_name}'"

            retries = 3
            for attempt in range(retries):
                try:
                    response = requests.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    data = response.json()

                    objects = data.get('objects', [])

                    status_entry = {
                        'Connection Name': conn_name,
                        'Connection Status': 'EXISTS' if len(objects) > 0 else 'MISSING'
                    }
                    connection_status_list.append(status_entry)

                    logger.debug(f"Connection {conn_name}: {status_entry['Connection Status']}")
                    break

                except requests.exceptions.RequestException as e:
                    if attempt < retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"Retry {attempt + 1} for connection {conn_name}: {str(e)}")
                        sleep(wait_time)
                    else:
                        logger.error(f"Failed to check connection {conn_name}")
                        status_entry = {
                            'Connection Name': conn_name,
                            'Connection Status': 'ERROR'
                        }
                        connection_status_list.append(status_entry)

        except Exception as e:
            logger.error(f"Error checking connection {conn_name}: {str(e)}")
            status_entry = {
                'Connection Name': conn_name,
                'Connection Status': 'ERROR'
            }
            connection_status_list.append(status_entry)

    logger.info(f"Connection status check completed for {len(connection_status_list)} connections")
    return connection_status_list
