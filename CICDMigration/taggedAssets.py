"""
Module for retrieving and processing tagged assets from IICS
"""
import requests
import math
from typing import List, Tuple, Dict
from .config import DICT_FILE_FORMAT, ASSETS_PER_PAGE, API_TIMEOUT
from .utils import retry_with_backoff


def generate_git_path(asset_path: str, formats: List[List], asset_type: str) -> List[str]:
    """
    Generate Git file paths for an asset based on its type and format

    Args:
        asset_path: Asset path in IICS (e.g., 'Project/Folder/AssetName')
        formats: List of format specifications
        asset_type: Type of the asset

    Returns:
        List of Git file paths
    """
    path_parts = asset_path.split('/')

    git_paths = []

    for format_spec in formats:
        has_dot = format_spec[0] == 1
        extension = format_spec[1]

        dot_prefix = '.' if has_dot else ''

        if len(path_parts) == 3:
            git_path = f"Explore/{path_parts[0]}/{path_parts[1]}/{dot_prefix}{path_parts[2]}.{asset_type}.{extension}"
        elif len(path_parts) == 2:
            git_path = f"Explore/{path_parts[0]}/{dot_prefix}{path_parts[1]}.{asset_type}.{extension}"
        else:
            continue

        git_paths.append(git_path)

    return git_paths


def retrieve_tagged_assets(
    session_id: str,
    base_api_url: str,
    tag: str,
    skip: int,
    logger
) -> dict:
    """
    Retrieve assets with a specific tag from IICS

    Args:
        session_id: IICS session ID
        base_api_url: Base API URL
        tag: Tag to filter assets
        skip: Number of records to skip (pagination)
        logger: Logger instance

    Returns:
        API response as dictionary

    Raises:
        Exception: If retrieval fails
    """
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'INFA-SESSION-ID': session_id,
    }

    url = f"{base_api_url}/public/core/v3/objects?q=tag=='{tag}'&skip={skip}"

    def make_request():
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        response.raise_for_status()
        return response

    try:
        response = retry_with_backoff(make_request, logger=logger)
        data = response.json()

        if 'objects' not in data or 'count' not in data:
            raise Exception("Invalid response structure from assets API")

        return data

    except requests.exceptions.RequestException as e:
        logger.critical(f"Failed to fetch assets: {str(e)}")
        raise Exception(f"Failed to fetch assets: {str(e)}") from e


def filter_and_parse_path(
    data: dict,
    session_id: str,
    base_api_url: str,
    project_name: str,
    tag: str,
    logger
) -> Tuple[List[str], List[Dict]]:
    """
    Filter assets by project and parse their paths

    Args:
        data: Initial API response
        session_id: IICS session ID
        base_api_url: Base API URL
        project_name: Project to filter by
        tag: Tag being processed
        logger: Logger instance

    Returns:
        Tuple of (git_paths_list, asset_metadata_list)
    """
    asset_count = data['count']

    if asset_count == 0:
        logger.warning(f"No assets found for tag '{tag}'")
        return [], []

    iterations = math.ceil(asset_count / ASSETS_PER_PAGE)

    git_paths = []
    asset_metadata = []

    for i in range(iterations):
        skip = ASSETS_PER_PAGE * i
        data_page = retrieve_tagged_assets(session_id, base_api_url, tag, skip, logger)

        for asset in data_page['objects']:
            project = asset['path'].split('/')[0]

            if project == project_name:
                asset_type = asset['type']

                if asset_type not in DICT_FILE_FORMAT:
                    logger.warning(f"Unsupported asset type: {asset_type} for {asset['path']}")
                    continue

                formats = DICT_FILE_FORMAT[asset_type]
                paths = generate_git_path(asset['path'], formats, asset_type)
                git_paths.extend(paths)

                asset_info = {
                    'path': asset['path'],
                    'type': asset_type
                }
                asset_metadata.append(asset_info)

        logger.info(f"Iteration {i + 1}/{iterations}: Retrieved {len(data_page['objects'])} assets")

    return git_paths, asset_metadata


def tagged_assets(
    data: dict,
    tags: List[str],
    project_name: str,
    logger
) -> Tuple[List[str], List[Dict]]:
    """
    Retrieve all assets for given tags

    Args:
        data: Session data containing sessionId and baseApiUrl
        tags: List of tags to retrieve
        project_name: Project to filter by
        logger: Logger instance

    Returns:
        Tuple of (unique_git_paths, unique_asset_metadata)

    Raises:
        Exception: If no assets found
    """
    logger.info(f"Retrieving assets based on tags: {tags}")

    all_git_paths = []
    all_metadata = []

    for tag in tags:
        logger.info(f"Processing tag: '{tag}'")

        asset_data = retrieve_tagged_assets(
            data['sessionId'],
            data['baseApiUrl'],
            tag,
            0,
            logger
        )

        git_paths, metadata = filter_and_parse_path(
            asset_data,
            data['sessionId'],
            data['baseApiUrl'],
            project_name,
            tag,
            logger
        )

        logger.info(f"Tag '{tag}' - Found {len(metadata)} assets in project '{project_name}'")

        all_git_paths.extend(git_paths)
        all_metadata.extend(metadata)

    unique_git_paths = list(dict.fromkeys(all_git_paths))
    unique_metadata = []
    seen_paths = set()

    for metadata_item in all_metadata:
        path_key = f"{metadata_item['path']}:{metadata_item['type']}"
        if path_key not in seen_paths:
            unique_metadata.append(metadata_item)
            seen_paths.add(path_key)

    logger.info(f"Total unique assets to migrate: {len(unique_metadata)}")

    if len(unique_metadata) == 0:
        raise Exception(f"No assets found with tags {tags} in project '{project_name}'")

    return unique_git_paths, unique_metadata
