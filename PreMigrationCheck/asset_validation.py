"""
Asset Validation Module for Pre-Migration Check
Checks for checked-out assets and invalid assets
"""
import math
import requests
import logging
from typing import List, Dict, Tuple
from time import sleep


# documentTypes queried by the frs/BaseEntities validity API (URL-encoded).
# Ported from the working reference implementation.
_VALIDITY_DOC_TYPES_FILTER = (
    "(documentType%20eq%20%27Folder%27%20or%20documentType%20eq%20%27API_COLLECTION%27%20or%20"
    "documentType%20eq%20%27SAAS_BSERVICES%27%20or%20documentType%20eq%20%27SAAS_DMASK%27%20or%20"
    "documentType%20eq%20%27SAAS_DRS%27%20or%20documentType%20eq%20%27SAAS_DSS%27%20or%20"
    "documentType%20eq%20%27DTT%27%20or%20documentType%20eq%20%27DLT%27%20or%20"
    "documentType%20eq%20%27BATCH_MAPPING%27%20or%20documentType%20eq%20%27SAAS_FWCONFIG%27%20or%20"
    "documentType%20eq%20%27SAAS_HSCHEMA%27%20or%20documentType%20eq%20%27MCT%27%20or%20"
    "documentType%20eq%20%27SAAS_CUSTOM_FUNC%27%20or%20documentType%20eq%20%27SAAS_PCTASK%27%20or%20"
    "documentType%20eq%20%27SAAS_SAVED_QUERY%27%20or%20documentType%20eq%20%27SAAS_STRUCTURE_DISCOVERY%27%20or%20"
    "documentType%20eq%20%27SEQUENCE_GEN%27%20or%20documentType%20eq%20%27SAAS_ITEMPLATE%27%20or%20"
    "documentType%20eq%20%27SAAS_LINEAR_TASKFLOW%27%20or%20documentType%20eq%20%27UDF%27%20or%20"
    "documentType%20eq%20%27MAPPING%27%20or%20documentType%20eq%20%27AT_SCALE_MAPPING%27%20or%20"
    "documentType%20eq%20%27ECOSYSTEM_MAPPING%27%20or%20documentType%20eq%20%27DMAPPLET%27%20or%20"
    "documentType%20eq%20%27SNOWFLAKE_INGEST%27%20or%20documentType%20eq%20%27DW_TASK%27%20or%20"
    "documentType%20eq%20%27AI_CONNECTION%27%20or%20documentType%20eq%20%27GUIDE%27%20or%20"
    "documentType%20eq%20%27PROCESS%27%20or%20documentType%20eq%20%27PROCESS_OBJECT%27%20or%20"
    "documentType%20eq%20%27AI_SERVICE_CONNECTOR%27%20or%20documentType%20eq%20%27TASKFLOW%27%20or%20"
    "documentType%20eq%20%27HUMAN_TASK%27%20or%20documentType%20eq%20%27cih_application%27%20or%20"
    "documentType%20eq%20%27cih_publication%27%20or%20documentType%20eq%20%27cih_subscription%27%20or%20"
    "documentType%20eq%20%27cih_topic%27%20or%20documentType%20eq%20%27IDSC%27%20or%20"
    "documentType%20eq%20%27MAPPLET_SAP_IDOC%27%20or%20documentType%20eq%20%27CLEANSE%27%20or%20"
    "documentType%20eq%20%27DEDUPLICATE%27%20or%20documentType%20eq%20%27PARSE%27%20or%20"
    "documentType%20eq%20%27RULE_SPECIFICATION%27%20or%20documentType%20eq%20%27DICTIONARY%27%20or%20"
    "documentType%20eq%20%27VERIFIER%27%20or%20documentType%20eq%20%27LABELER%27%20or%20"
    "documentType%20eq%20%27EXCEPTION%27%20or%20documentType%20eq%20%27DBMI_TASK%27%20or%20"
    "documentType%20eq%20%27APPMI_TASK%27%20or%20documentType%20eq%20%27MI_TASK%27%20or%20"
    "documentType%20eq%20%27SI_DATAFLOW%27%20or%20documentType%20eq%20%27MI_FILE_LISTENER%27%20or%20"
    "documentType%20eq%20%27PROFILE%27)"
)


def get_checked_out_assets(session_id: str, base_api_url: str, assets: List[Dict],
                           project_name: str, logger: logging.Logger) -> Tuple[List[Dict], List[Dict]]:
    """
    Check which assets are checked out

    Args:
        session_id: IICS session ID
        base_api_url: Base API URL
        assets: List of asset dictionaries
        project_name: Project name to filter
        logger: Logger instance

    Returns:
        Tuple of (checked_out_list, asset_list_for_excel)
    """
    logger.info(f"Checking checkout status for {len(assets)} assets")

    checked_out_assets = []
    asset_list_excel = []

    # Checkout status is already present in each asset's 'sourceControl' block
    # (returned by the tag/objects listing). An asset is checked out when
    # sourceControl.checkedOutBy is set, so we read it directly instead of making
    # a separate per-asset API call (the /objects/{id} endpoint was returning 404).
    for asset in assets:
        path = asset.get('path', '')

        # Filter by project
        if not path.startswith(f"{project_name}/"):
            continue

        source_control = asset.get('sourceControl') or {}
        checked_out_by = source_control.get('checkedOutBy')

        if checked_out_by:
            checked_out_assets.append(asset)

            # Derive a readable asset name from the path (the listing has no
            # 'name' field), then parse project/folder for the Excel report.
            path_parts = path.split('/')
            asset_name = path_parts[-1] if path_parts else asset.get('name', 'Unknown')
            excel_entry = {
                'Project': path_parts[0] if len(path_parts) > 0 else 'N/A',
                'Folder': path_parts[1] if len(path_parts) > 2 else 'N/A',
                'Asset': asset_name,
                'Checked Out By': checked_out_by,
                'Checked Out Time': source_control.get('checkedOutTime', 'N/A')
            }
            asset_list_excel.append(excel_entry)

            logger.debug(f"Checked out asset: {asset_name} (by {checked_out_by})")

    logger.info(f"Found {len(checked_out_assets)} checked-out assets")
    return checked_out_assets, asset_list_excel


def validate_assets(session_id: str, base_api_url: str, assets: List[Dict],
                    project_name: str, logger: logging.Logger) -> List[Dict]:
    """
    Find assets whose validation state is not VALID.

    Asset validity is NOT exposed by the /public/core/v3/objects listing; it
    comes from the frs/api/v1/BaseEntities endpoint, which returns a
    'documentState' per asset. Anything other than 'VALID' (e.g. INVALID) is
    reported. Ported from the working reference implementation.

    The 'assets' argument (the tagged asset list) is only used to scope which
    assets we care about - validity itself is read from BaseEntities.

    Args:
        session_id: IICS session ID (reused for the frs call via IDS-SESSION-ID)
        base_api_url: Base API URL from login
        assets: List of tagged asset dictionaries (used to scope by id)
        project_name: Project name to filter
        logger: Logger instance

    Returns:
        List of invalid asset dictionaries (Project Name, Asset, Asset Type).
    """
    logger.info(f"Validating {len(assets)} assets")

    invalid_assets = []

    # Ids of the tagged assets in this project - we only report validity for
    # assets that are actually in scope for this migration.
    tagged_ids = {
        a.get('id') for a in assets
        if a.get('id') and (a.get('path') or '').startswith(f"{project_name}/")
    }

    try:
        state_by_id = _fetch_document_states(session_id, base_api_url, project_name, logger)
    except Exception as e:
        logger.error(f"Failed to fetch asset validity from BaseEntities: {str(e)}")
        logger.info("Found 0 invalid assets (validity lookup failed)")
        return invalid_assets

    for asset_id, (name, doc_type, state) in state_by_id.items():
        # Only report assets that were part of the tagged migration set
        if asset_id not in tagged_ids:
            continue

        if state and state != 'VALID':
            invalid_assets.append({
                'Project Name': project_name,
                'Asset': name,
                'Asset Type': doc_type,
                'Status': state
            })
            logger.debug(f"Invalid asset: {name} ({doc_type}) - state={state}")

    logger.info(f"Found {len(invalid_assets)} invalid assets")
    return invalid_assets


def _fetch_document_states(session_id: str, base_api_url: str,
                           project_name: str, logger: logging.Logger) -> Dict[str, list]:
    """
    Fetch documentState for all assets in a project via frs/api/v1/BaseEntities.

    Args:
        session_id: IICS session ID (sent as IDS-SESSION-ID)
        base_api_url: Base API URL from login (the '/saas' segment is stripped)
        project_name: Project to filter by (matched on parentInfo parentName)
        logger: Logger instance

    Returns:
        Dict mapping asset id -> [name, documentType, documentState].
    """
    # The frs endpoint lives at the org root, not under /saas
    modified_server_url = base_api_url.replace("/saas", "")

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'IDS-SESSION-ID': session_id,
    }

    def _build_url(skip: int) -> str:
        return (
            f"{modified_server_url}/frs/api/v1/BaseEntities"
            f"?$count=true&$expand=userInfo,sourceControlAttributes,tags"
            f"&recurseContainer=false&$top=200&$skip={skip}"
            f"&$orderby=lastUpdatedTime%20desc&$filter={_VALIDITY_DOC_TYPES_FILTER}"
        )

    # First call to get the total count
    response = requests.get(_build_url(0), headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()

    total_count = data.get('@odata.count', 0)
    logger.info(f"BaseEntities total count: {total_count}")

    state_by_id: Dict[str, list] = {}
    iterations = math.ceil(total_count / 200) if total_count else 0

    for i in range(iterations):
        skip = 200 * i
        page = requests.get(_build_url(skip), headers=headers, timeout=60)
        page.raise_for_status()
        page_data = page.json()

        for item in page_data.get('value', []):
            # parentInfo[1].parentName is the project; skip folders themselves
            parent_info = item.get('parentInfo') or []
            if len(parent_info) < 2:
                continue

            if parent_info[1].get('parentName') == project_name and item.get('documentType') != 'Folder':
                state_by_id[item['id']] = [
                    item.get('name'),
                    item.get('documentType'),
                    item.get('documentState')
                ]

    logger.info(f"BaseEntities: found {len(state_by_id)} assets in project '{project_name}'")
    return state_by_id
