"""
Connection Status Check Module for Pre-Migration Check

Connection dependencies are discovered via the IICS export API (export the
in-project assets with includeDependencies=True, then read the export's object
list and pick out the CONNECTION entries). This matches the working reference
implementation - the /objects/{id} 'metadata.connections' field used previously
does not exist, so it always found zero.
"""
import json
import requests
import logging
from typing import List, Dict
from time import sleep


def get_connection_dependencies(session_id: str, base_api_url: str, assets: List[Dict],
                                project_name: str, logger: logging.Logger) -> List[str]:
    """
    Discover connection dependencies for the in-project assets via the export API.

    Args:
        session_id: Source IICS session ID
        base_api_url: Source base API URL
        assets: List of asset dictionaries (tagged assets)
        project_name: Project name to filter
        logger: Logger instance

    Returns:
        List of unique connection names the assets depend on.
    """
    logger.info(f"Extracting connection dependencies from {len(assets)} assets")

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'INFA-SESSION-ID': session_id,
    }

    # Build the export body: every in-project asset, with dependencies included.
    export_body = [
        {"id": asset['id'], "includeDependencies": True}
        for asset in assets
        if asset.get('id') and (asset.get('path') or '').startswith(f"{project_name}/")
    ]

    if not export_body:
        logger.info("No in-project assets to check for connection dependencies")
        return []

    try:
        # Step 1: kick off an export job for the assets + their dependencies
        export_url = f"{base_api_url}/public/core/v3/export"
        payload = json.dumps({"name": project_name, "objects": export_body})
        export_resp = requests.post(export_url, data=payload, headers=headers, timeout=60)
        export_resp.raise_for_status()
        export_id = export_resp.json().get('id')

        if not export_id:
            logger.error("Export API did not return a job id; cannot resolve dependencies")
            return []

        # Step 2: read the export's resolved object list (includes dependencies).
        # The job may take a moment to populate, so retry a few times.
        dep_url = f"{base_api_url}/public/core/v3/export/{export_id}?expand=objects"
        objects = []
        for attempt in range(5):
            dep_resp = requests.get(dep_url, headers=headers, timeout=60)
            dep_resp.raise_for_status()
            dep_data = dep_resp.json()
            objects = dep_data.get('objects', [])
            if objects:
                break
            sleep(2)

        # Step 3: pick out the connection dependencies (unique, order-preserving)
        connection_names = list(dict.fromkeys(
            obj.get('name')
            for obj in objects
            if obj.get('type') == 'Connection' and obj.get('name')
        ))

        logger.info(f"Found {len(connection_names)} unique connection dependencies")
        return connection_names

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to resolve connection dependencies via export API: {str(e)}")
        return []


def check_connection_status_in_target(session_id: str, base_api_url: str,
                                      connection_names: List[str], logger: logging.Logger) -> List[Dict]:
    """
    Check which of the given connections exist in the target environment.

    Lists all CONNECTION objects in the target once, then compares by name -
    more efficient than one query per connection.

    Args:
        session_id: Target IICS session ID
        base_api_url: Target base API URL
        connection_names: List of connection names to check
        logger: Logger instance

    Returns:
        List of {Connection Name, Connection Status} dicts. Status is
        'Available' or 'Not Available'.
    """
    logger.info(f"Checking status of {len(connection_names)} connections in target")

    if not connection_names:
        logger.info("Connection status check completed for 0 connections")
        return []

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'INFA-SESSION-ID': session_id,
    }

    # Fetch all target connection names once
    target_connection_names = set()
    try:
        url = f"{base_api_url}/public/core/v3/objects?q=type=='CONNECTION'"
        skip = 0
        while True:
            page_url = f"{url}&skip={skip}"
            response = requests.get(page_url, headers=headers, timeout=30)
            response.raise_for_status()
            objects = response.json().get('objects', [])
            if not objects:
                break
            for obj in objects:
                if obj.get('name'):
                    target_connection_names.add(obj['name'])
            if len(objects) < 200:
                break
            skip += 200
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to list target connections: {str(e)}")
        # Fall back to reporting everything as unknown rather than crashing
        return [
            {'Connection Name': name, 'Connection Status': 'ERROR'}
            for name in connection_names
        ]

    connection_status_list = []
    for conn_name in connection_names:
        status = 'Available' if conn_name in target_connection_names else 'Not Available'
        connection_status_list.append({
            'Connection Name': conn_name,
            'Connection Status': status
        })
        logger.debug(f"Connection {conn_name}: {status}")

    logger.info(f"Connection status check completed for {len(connection_status_list)} connections")
    return connection_status_list
