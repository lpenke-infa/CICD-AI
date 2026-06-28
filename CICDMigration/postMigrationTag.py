"""
Module for tagging assets after migration
"""
import json
import requests
from typing import List, Dict
from .config import TAG_BATCH_SIZE, API_TIMEOUT
from .utils import retry_with_backoff


def lookup_v3(
    session_id: str,
    base_api_url: str,
    asset_metadata: List[Dict],
    post_migration_tags: List[str],
    logger
) -> List[Dict]:
    """
    Lookup asset IDs for tagging

    Args:
        session_id: IICS session ID
        base_api_url: Base API URL
        asset_metadata: List of asset metadata dictionaries
        post_migration_tags: Tags to apply
        logger: Logger instance

    Returns:
        List of tag request objects with asset IDs

    Raises:
        Exception: If lookup fails
    """
    url = f"{base_api_url}/public/core/v3/lookup"

    payload = {
        "objects": asset_metadata
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

        if 'objects' not in result:
            raise Exception("Invalid response structure from lookup API")

        tag_request_body = []

        for obj in result["objects"]:
            if 'id' not in obj:
                logger.warning(f"Object missing ID, skipping: {obj}")
                continue

            tag_request_body.append({
                "id": obj['id'],
                "tags": post_migration_tags
            })

        logger.info(f"Created tag request for {len(tag_request_body)} assets")
        return tag_request_body

    except requests.exceptions.RequestException as e:
        logger.critical(f"Lookup API error: {str(e)}")
        raise Exception(f"Lookup failed: {str(e)}") from e


def post_migration_tagging_v3(
    session_id: str,
    base_api_url: str,
    tag_request_body: List[Dict],
    logger
) -> bool:
    """
    Apply post-migration tags to assets in batches

    Args:
        session_id: IICS session ID
        base_api_url: Base API URL
        tag_request_body: List of tag requests
        logger: Logger instance

    Returns:
        True if all tagging succeeded

    Raises:
        Exception: If tagging fails
    """
    url = f"{base_api_url}/public/core/v3/TagObjects"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "INFA-SESSION-ID": session_id
    }

    total_batches = (len(tag_request_body) + TAG_BATCH_SIZE - 1) // TAG_BATCH_SIZE
    tagged_count = 0

    for i in range(0, len(tag_request_body), TAG_BATCH_SIZE):
        batch_num = (i // TAG_BATCH_SIZE) + 1
        current_batch = tag_request_body[i:i + TAG_BATCH_SIZE]

        payload = json.dumps(current_batch, indent=4)

        def make_request():
            response = requests.post(
                url,
                data=payload,
                headers=headers,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            return response

        try:
            response = retry_with_backoff(make_request, logger=logger)
            status_code = response.status_code

            if status_code in [204, 207]:
                tagged_count += len(current_batch)
                logger.info(
                    f"Batch {batch_num}/{total_batches}: "
                    f"Successfully tagged {len(current_batch)} assets"
                )
            else:
                logger.error(
                    f"Batch {batch_num}/{total_batches}: "
                    f"Unexpected status code {status_code}"
                )
                raise Exception(f"Unexpected status code: {status_code}")

        except requests.exceptions.RequestException as e:
            logger.critical(f"Tagging failed for batch {batch_num}: {str(e)}")
            raise Exception(f"Tagging failed: {str(e)}") from e

    logger.info(f"Successfully tagged {tagged_count} assets")
    return True


def post_migration_tag(
    asset_metadata: List[Dict],
    tgt_data: dict,
    post_migration_tags: List[str],
    logger
) -> bool:
    """
    Apply post-migration tags to assets in target environment

    Args:
        asset_metadata: List of asset metadata dictionaries
        tgt_data: Target IICS session data
        post_migration_tags: Tags to apply
        logger: Logger instance

    Returns:
        True if successful

    Raises:
        Exception: If tagging fails
    """
    logger.info(f"Starting post-migration tagging with tags: {post_migration_tags}")

    tag_request_body = lookup_v3(
        tgt_data['sessionId'],
        tgt_data['baseApiUrl'],
        asset_metadata,
        post_migration_tags,
        logger
    )

    if not tag_request_body:
        logger.warning("No assets to tag")
        return False

    result = post_migration_tagging_v3(
        tgt_data['sessionId'],
        tgt_data['baseApiUrl'],
        tag_request_body,
        logger
    )

    logger.info("Post-migration tagging completed successfully")
    return result
