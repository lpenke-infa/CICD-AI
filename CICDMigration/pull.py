"""
Module for pulling assets from Git to IICS target environment
"""
import json
import requests
import time
from typing import List, Dict
from .config import API_TIMEOUT, PULL_STATUS_CHECK_INTERVAL
from .utils import retry_with_backoff


def pull_v3(
    session_id: str,
    base_api_url: str,
    commit_hash: str,
    asset_metadata: List[Dict],
    logger
) -> dict:
    """
    Initiate a pull operation using IICS REST V3 API

    Args:
        session_id: IICS session ID
        base_api_url: Base API URL
        commit_hash: Git commit hash to pull from
        asset_metadata: List of asset metadata dictionaries
        logger: Logger instance

    Returns:
        API response containing pullActionId

    Raises:
        Exception: If pull initiation fails
    """
    logger.info("Initiating pull using IICS REST V3 API")

    url = f"{base_api_url}/public/core/v3/pull"

    object_list = [
        {
            'path': item['path'].split('/'),
            'type': item['type']
        }
        for item in asset_metadata
    ]

    payload = {
        "commitHash": commit_hash,
        "objects": object_list
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "INFA-SESSION-ID": session_id
    }

    def make_request():
        response = requests.post(
            url,
            data=json.dumps(payload, indent=4),
            headers=headers,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return response

    try:
        response = retry_with_backoff(make_request, logger=logger)
        result = response.json()

        if 'pullActionId' not in result:
            raise Exception("pullActionId not found in response")

        logger.info(f"Pull initiated successfully. Pull Action ID: {result['pullActionId']}")
        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            logger.error("Authentication failed during pull operation")
            raise Exception("Pull failed: Authentication error") from e
        raise Exception(f"Pull failed: {str(e)}") from e

    except requests.exceptions.RequestException as e:
        logger.critical(f"Pull request failed: {str(e)}")
        raise Exception(f"Pull failed: {str(e)}") from e


def get_pull_status_v3(
    session_id: str,
    base_api_url: str,
    pull_action_id: str,
    logger
) -> dict:
    """
    Monitor pull operation status until completion

    Args:
        session_id: IICS session ID
        base_api_url: Base API URL
        pull_action_id: Pull action ID from pull initiation
        logger: Logger instance

    Returns:
        Final pull status response

    Raises:
        Exception: If pull fails or is cancelled
    """
    logger.info("Monitoring pull operation status")

    url = f"{base_api_url}/public/core/v3/pull/{pull_action_id}?expand=objects"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "INFA-SESSION-ID": session_id
    }

    max_iterations = 120
    iteration = 0

    try:
        while iteration < max_iterations:
            iteration += 1

            response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
            response.raise_for_status()
            result = response.json()

            if 'status' not in result or 'state' not in result['status']:
                raise Exception("Invalid response structure from pull status API")

            state = result['status']['state']
            logger.info(f"Pull State (check {iteration}): {state}")

            if state == 'SUCCESSFUL':
                logger.info("Pull completed successfully")
                return result

            if state == 'FAILED':
                logger.critical("Pull operation FAILED")

                if 'objects' in result:
                    for item in result['objects']:
                        if item.get('status', {}).get('state') == 'FAILED':
                            asset_path = "/".join(item['target']['path'])
                            error_msg = item['status'].get('message', 'Unknown error')
                            logger.critical(f"Failed asset: {asset_path} - {error_msg}")

                raise Exception("Pull operation failed")

            if state == 'CANCELLED':
                logger.critical("Pull operation CANCELLED")
                raise Exception("Pull operation was cancelled")

            time.sleep(PULL_STATUS_CHECK_INTERVAL)

        raise Exception(f"Pull operation timed out after {max_iterations} checks")

    except requests.exceptions.RequestException as e:
        logger.critical(f"Error checking pull status: {str(e)}")
        raise Exception(f"Pull status check failed: {str(e)}") from e


def pull_assets(
    asset_metadata: List[Dict],
    commit_hash: str,
    tgt_data: dict,
    logger
) -> dict:
    """
    Pull assets from Git to IICS target environment

    Args:
        asset_metadata: List of asset metadata dictionaries
        commit_hash: Git commit hash to pull from
        tgt_data: Target IICS session data
        logger: Logger instance

    Returns:
        Final pull status

    Raises:
        Exception: If pull fails
    """
    logger.info(f"Starting pull operation for {len(asset_metadata)} assets")
    logger.info(f"Commit Hash: {commit_hash}")

    response = pull_v3(
        tgt_data['sessionId'],
        tgt_data['baseApiUrl'],
        commit_hash,
        asset_metadata,
        logger
    )

    pull_action_id = response['pullActionId']

    final_status = get_pull_status_v3(
        tgt_data['sessionId'],
        tgt_data['baseApiUrl'],
        pull_action_id,
        logger
    )

    logger.info("Pull operation completed successfully")
    return final_status
