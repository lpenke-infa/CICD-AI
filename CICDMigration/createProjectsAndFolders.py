"""
Module for creating projects and folders in IICS target environment
"""
import json
import requests
from typing import Dict, List
from .config import API_TIMEOUT
from .utils import retry_with_backoff


def extract_folder_and_project(asset_metadata: List[Dict]) -> Dict[str, List[str]]:
    """
    Extract unique projects and folders from asset metadata

    Args:
        asset_metadata: List of asset metadata dictionaries

    Returns:
        Dictionary mapping project names to list of folder names
    """
    structure = {}

    for item in asset_metadata:
        path_parts = item['path'].split('/')

        if len(path_parts) == 2:
            project_name = path_parts[0]
            folder_name = ""
        elif len(path_parts) >= 3:
            project_name = path_parts[0]
            folder_name = path_parts[1]
        else:
            continue

        if project_name in structure:
            if folder_name and folder_name not in structure[project_name]:
                structure[project_name].append(folder_name)
        else:
            if folder_name:
                structure[project_name] = [folder_name]
            else:
                structure[project_name] = []

    return structure


def is_project_or_folder_exists(
    location_path: str,
    session_id: str,
    base_api_url: str,
    logger
) -> bool:
    """
    Check if a project or folder exists

    Args:
        location_path: Path to check (e.g., 'ProjectName' or 'ProjectName/FolderName')
        session_id: IICS session ID
        base_api_url: Base API URL
        logger: Logger instance

    Returns:
        True if exists, False otherwise
    """
    url = f"{base_api_url}/public/core/v3/objects?q=location=='{location_path}'"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "INFA-SESSION-ID": session_id
    }

    try:
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error checking existence of {location_path}: {str(e)}")
        return False


def create_project(
    project_name: str,
    session_id: str,
    base_api_url: str,
    logger
) -> dict:
    """
    Create a new project

    Args:
        project_name: Name of the project
        session_id: IICS session ID
        base_api_url: Base API URL
        logger: Logger instance

    Returns:
        API response with project details

    Raises:
        Exception: If creation fails
    """
    url = base_api_url.replace('/saas', '') + "/frs/v1/Projects"

    payload = {
        "name": project_name,
        "description": f"Created {project_name} via CICD automation"
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "IDS-SESSION-ID": session_id
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

        if 'id' not in result:
            raise Exception("Project ID not found in response")

        logger.info(f"Project created: {project_name}")
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create project {project_name}: {str(e)}")
        raise Exception(f"Project creation failed: {str(e)}") from e


def get_project_id(
    project_name: str,
    session_id: str,
    base_api_url: str,
    logger
) -> str:
    """
    Get project ID by name

    Args:
        project_name: Name of the project
        session_id: IICS session ID
        base_api_url: Base API URL
        logger: Logger instance

    Returns:
        Project ID

    Raises:
        Exception: If project not found
    """
    url = base_api_url.replace('/saas', '') + f"/frs/v1/Projects?$filter=(name eq '{project_name}')"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "IDS-SESSION-ID": session_id
    }

    try:
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        response.raise_for_status()
        result = response.json()

        if 'value' not in result or len(result['value']) == 0:
            raise Exception(f"Project {project_name} not found")

        return result['value'][0]['id']

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get project ID for {project_name}: {str(e)}")
        raise Exception(f"Failed to get project ID: {str(e)}") from e


def create_folder(
    folder_name: str,
    project_id: str,
    session_id: str,
    base_api_url: str,
    logger
) -> dict:
    """
    Create a new folder in a project

    Args:
        folder_name: Name of the folder
        project_id: Parent project ID
        session_id: IICS session ID
        base_api_url: Base API URL
        logger: Logger instance

    Returns:
        API response with folder details

    Raises:
        Exception: If creation fails
    """
    url = base_api_url.replace('/saas', '') + f"/frs/v1/Projects('{project_id}')/Folders"

    payload = {
        "name": folder_name,
        "description": f"Created {folder_name} via CICD automation"
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "IDS-SESSION-ID": session_id
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
        logger.info(f"Folder created: {folder_name}")
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create folder {folder_name}: {str(e)}")
        raise Exception(f"Folder creation failed: {str(e)}") from e


def create_projects_and_folders(
    asset_metadata: List[Dict],
    session_id: str,
    base_api_url: str,
    logger
) -> bool:
    """
    Create required projects and folders in target environment

    Args:
        asset_metadata: List of asset metadata dictionaries
        session_id: IICS session ID
        base_api_url: Base API URL
        logger: Logger instance

    Returns:
        True if successful

    Raises:
        Exception: If creation fails
    """
    logger.info("Creating required projects and folders")

    structure = extract_folder_and_project(asset_metadata)

    for project_name, folders in structure.items():
        logger.info(f"Processing project: {project_name}")

        project_exists = is_project_or_folder_exists(
            project_name,
            session_id,
            base_api_url,
            logger
        )

        if project_exists:
            logger.info(f"  Project '{project_name}' already exists")
            project_id = get_project_id(project_name, session_id, base_api_url, logger)
        else:
            logger.info(f"  Project '{project_name}' does not exist, creating...")
            project_response = create_project(project_name, session_id, base_api_url, logger)
            project_id = project_response['id']

        for folder in folders:
            logger.info(f"  Processing folder: {folder}")

            folder_path = f"{project_name}/{folder}"
            folder_exists = is_project_or_folder_exists(
                folder_path,
                session_id,
                base_api_url,
                logger
            )

            if folder_exists:
                logger.info(f"    Folder '{folder}' already exists")
            else:
                logger.info(f"    Folder '{folder}' does not exist, creating...")
                create_folder(folder, project_id, session_id, base_api_url, logger)

    logger.info("Projects and folders setup completed")
    return True
