"""
IICS authentication module
"""
import requests
import json
from typing import Dict
from .config import API_TIMEOUT
from .utils import retry_with_backoff


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
        response = requests.post(url, headers=headers, data=payload, timeout=API_TIMEOUT)
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


def iics_login(username: str, password: str, region: str, logger) -> Dict[str, str]:
    """
    Wrapper function for IICS login

    Args:
        username: IICS username
        password: IICS password
        region: IICS region
        logger: Logger instance

    Returns:
        Dictionary containing session and org information
    """
    return login(username, password, region, logger)