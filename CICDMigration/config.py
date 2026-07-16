"""
Configuration constants for IICS CI/CD automation
"""
from typing import Dict, List

API_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2
GIT_OPERATION_TIMEOUT = 300
PULL_STATUS_CHECK_INTERVAL = 15
ASSETS_PER_PAGE = 200
TAG_BATCH_SIZE = 100

DICT_FILE_FORMAT: Dict[str, List[List]] = {
    'DTEMPLATE': [[1, 'json'], [0, 'zip']],
    'MTT': [[1, 'json'], [0, 'zip']],
    'TASKFLOW': [[1, 'json'], [0, 'xml']],
    'AtScaleDTemplate': [[1, 'json'], [0, 'zip']],
    'DTT': [[1, 'json'], [0, 'dat']],
    'DBMI_TASK': [[1, 'json'], [0, 'dat']],
    'DICTIONARY': [[1, 'json'], [0, 'json']],
    'BSERVICE': [[1, 'json'], [0, 'zip']],
    'CLEANSE': [[1, 'json'], [0, 'json']],
    'DMAPPLET': [[1, 'json'], [0, 'zip']],
    'PARSE': [[1, 'json'], [0, 'json']],
    'RULE_SPECIFICATION': [[1, 'json'], [0, 'json']],
    'VERIFIER': [[1, 'json'], [0, 'json']],
    'LABELER': [[1, 'json'], [0, 'json']],
    'AI_CONNECTION': [[1, 'json'], [0, 'xml']],
    'PROCESS_OBJECT': [[1, 'json'], [0, 'xml']],
    'GUIDE': [[1, 'json'], [0, 'xml']],
    'AI_SERVICE_CONNECTOR': [[1, 'json'], [0, 'xml']],
    'PROCESS': [[1, 'json'], [0, 'xml']],
    'MI_FILE_LISTENER': [[1, 'json'], [0, 'dat']],
    'MI_TASK': [[1, 'json'], [0, 'dat']],
    'STRUCTURE_DISCOVERY': [[1, 'json'], [0, 'zip']],
    'UDF': [[1, 'json'], [0, 'zip']],
    'FWCONFIG': [[0, 'vc.json'], [0, 'zip'], [1, 'json']]
}
