"""
IICS authentication module for PreMigrationCheck
"""
import requests
import json
from typing import Dict
from time import sleep


def retry_with_backoff(func, max_retries=3, logger=None):
    """
    Retry function with exponential backoff

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        logger: Logger instance

    Returns:
        Result from successful function call

    Raises:
        Exception from last failed attempt
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                if logger:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                sleep(wait_time)
            else:
                if logger:
                    logger.error(f"All {max_retries} attempts failed")
                raise


def login(username: str, password: str, region: str, logger) -> Dict[str, str]:
    """
    Authenticate to IICS platform

    Args:
        username: IICS username
        password: IICS password
        region: IICS region (e.g., 'dm-us')
        logger: Logger instance

    Returns:
        Dictionary containing sessionId, baseApiUrl, orgId, orgName

    Raises:
        requests.exceptions.RequestException: If authentication fails
    """
    url = f"https://{region}.informaticacloud.com/saas/public/core/v3/login"

    payload = json.dumps({
        "username": username,
        "password": password
    })

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    def make_request():
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        response.raise_for_status()
        return response

    try:
        response = retry_with_backoff(make_request, logger=logger)
        logger.info(f'IDMC Platform Authentication Successful: Status {response.status_code}')

        data = response.json()

        if 'userInfo' not in data or 'products' not in data or len(data['products']) == 0:
            raise ValueError("Invalid response structure from login API")

        result = {
            'sessionId': data['userInfo']['sessionId'],
            'baseApiUrl': data['products'][0]['baseApiUrl'],
            'orgId': data['userInfo']['orgId'],
            'orgName': data['userInfo']['orgName']
        }

        return result

    except requests.exceptions.RequestException as e:
        logger.critical(f"IDMC Login Failed: {str(e)}")
        raise
