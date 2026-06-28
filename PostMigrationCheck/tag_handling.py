"""
Tag Handling Module for Post-Migration Validation
"""
import requests
import logging
import math
from typing import List, Dict
from time import sleep


def get_tagged_objects(session_id: str, base_api_url: str, tag: str, logger: logging.Logger) -> List[Dict]:
    """
    Retrieve all objects with a specific tag from IICS

    Args:
        session_id: IICS session ID
        base_api_url: Base API URL
        tag: Tag name to search for
        logger: Logger instance

    Returns:
        List of asset dictionaries

    Raises:
        requests.exceptions.RequestException: If API call fails
    """
    logger.info(f"Retrieving objects with tag: {tag}")

    all_objects = []
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'INFA-SESSION-ID': session_id,
    }

    # Get total count first
    count_url = f"{base_api_url}/public/core/v3/objects?q=tag=='{tag}'"

    try:
        response = requests.get(count_url, headers=headers, timeout=30)
        response.raise_for_status()
        total_count = response.json().get('count', 0)

        logger.info(f"Total objects found: {total_count}")

        if total_count == 0:
            return all_objects

        # Calculate iterations (200 items per page)
        iterations = math.ceil(total_count / 200)
        logger.info(f"Fetching in {iterations} iteration(s)")

        for i in range(iterations):
            skip = 200 * i
            page_url = f"{base_api_url}/public/core/v3/objects?q=tag=='{tag}'&skip={skip}"

            retries = 3
            for attempt in range(retries):
                try:
                    response = requests.get(page_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    page_data = response.json()

                    objects = page_data.get('objects', [])
                    all_objects.extend(objects)

                    logger.debug(f"Fetched {len(objects)} objects (skip={skip})")
                    break

                except requests.exceptions.RequestException as e:
                    if attempt < retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"API call failed, retrying in {wait_time}s: {str(e)}")
                        sleep(wait_time)
                    else:
                        logger.error(f"Failed to fetch page after {retries} attempts")
                        raise

        logger.info(f"Successfully retrieved {len(all_objects)} objects")
        return all_objects

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to retrieve tagged objects: {str(e)}")
        raise


def get_assets_by_tags(session_id: str, base_api_url: str, tags: List[str], logger: logging.Logger) -> List[Dict]:
    """
    Retrieve all unique assets matching any of the provided tags

    Args:
        session_id: IICS session ID
        base_api_url: Base API URL
        tags: List of tag names to search for
        logger: Logger instance

    Returns:
        List of unique asset dictionaries
    """
    logger.info(f"Retrieving assets for {len(tags)} tag(s)")

    all_assets = []
    seen_ids = set()

    for tag in tags:
        try:
            assets = get_tagged_objects(session_id, base_api_url, tag, logger)

            for asset in assets:
                asset_id = asset.get('id')
                if asset_id and asset_id not in seen_ids:
                    all_assets.append(asset)
                    seen_ids.add(asset_id)

        except Exception as e:
            logger.error(f"Failed to retrieve assets for tag '{tag}': {str(e)}")
            continue

    logger.info(f"Total unique assets retrieved: {len(all_assets)}")
    return all_assets
