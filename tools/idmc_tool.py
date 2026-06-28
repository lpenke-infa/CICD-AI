"""
IDMC Operations Tool - Reusable module for IDMC API operations
"""

import os
import logging
import json
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def create_idmc_logger(log_dir: str = "Logs") -> logging.Logger:
    """
    Create and configure logger for IDMC operations

    Args:
        log_dir: Directory path for log files

    Returns:
        Configured logger instance
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_filename = 'IDMCFunctionalities.log'

    idmc_logger = logging.getLogger('IDMCFunctionalities')

    if idmc_logger.hasHandlers():
        idmc_logger.handlers.clear()

    idmc_logger.propagate = False
    idmc_logger.setLevel(logging.INFO)

    # File handler with append mode
    file_handler = logging.FileHandler(
        os.path.join(log_dir, log_filename),
        mode='a',
        encoding='utf-8'
    )
    stream_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    file_handler.setLevel(logging.INFO)
    stream_handler.setLevel(logging.INFO)

    idmc_logger.addHandler(file_handler)
    idmc_logger.addHandler(stream_handler)

    # Log session separator
    idmc_logger.info("="*80)
    idmc_logger.info(f"IDMC Functionalities Session Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    idmc_logger.info("="*80)

    return idmc_logger


@tool
def idmc_operations_tool(
    username: str,
    password: str,
    region: str,
    operation: str,
    parameters: str,
    is_count_query: bool = False
) -> str:
    """
    IDMC Operations Tool - Execute various IDMC operations.

    Supports comprehensive IDMC operations including:
    - Asset Management: Get objects, query by type/path
    - Tag Management: Add/remove tags from assets
    - Project Management: Create, update, delete projects
    - Folder Management: Create, update, delete folders
    - Schedule Management: Get, create, update, delete schedules
    - User Management: Get, create, delete users
    - Agent Management: Get agents, runtime environments, agent status
    - Permission Management: Get, create, update, delete object permissions

    Args:
        username: IDMC username
        password: IDMC password
        region: IDMC region (e.g., 'dm-us', 'dm-eu')
        operation: Operation to perform. Supported operations:
                  - 'get_objects': Get IDMC objects (with optional filters)
                  - 'tag_assets': Add tags to assets
                  - 'untag_assets': Remove tags from assets
                  - 'create_project': Create a new project
                  - 'update_project': Update project details
                  - 'delete_project': Delete an empty project
                  - 'create_folder': Create a new folder
                  - 'update_folder': Update folder details
                  - 'delete_folder': Delete an empty folder
                  - 'get_schedules': Get schedule information
                  - 'create_schedule': Create a new schedule
                  - 'update_schedule': Update existing schedule
                  - 'delete_schedule': Delete a schedule
                  - 'get_agents': Get secure agents
                  - 'get_agent_status': Get agent service status
                  - 'get_runtime_environments': Get runtime environments
                  - 'get_users': Get organization users
                  - 'create_user': Create a new user
                  - 'delete_user': Delete a user
        parameters: JSON string containing operation-specific parameters
        is_count_query: Set to True if the user only wants the count (e.g., "how many mappings", "give me count")
                       When True, only the count will be returned without generating reports or detailed lists

    Returns:
        JSON string with operation results

    Example parameters for different operations:
        get_objects: {"ObjectType": "DTEMPLATE"}  # Get all mappings
        get_objects: {"PathFilter": "Project/Folder"}  # Get assets in folder
        get_objects: {"QueryFilter": "tags contains 'MyTag'"}  # Get assets with specific tag
        get_objects: {"QueryFilter": "type=='MTT' and tags contains 'Production'"}  # Combined filters
        tag_assets: {"Assets": [{"id": "asset123", "tags": ["TAG1", "TAG2"]}]}
        create_project: {"ProjectName": "NewProject", "ProjectDescription": "Description"}

    Query Filter Syntax:
        - Tags: tags contains 'TagName'
        - Type: type=='DTEMPLATE'
        - Path: path=='Project/Folder'
        - Name: name contains 'SearchText'
        - Combine with: and, or operators

    IMPORTANT - COUNT QUERIES:
    When the user asks questions like:
    - "how many mappings"
    - "give me count of projects"
    - "total number of users"
    Set is_count_query=True to return ONLY the count without generating reports.

    IMPORTANT - TAGGING RESTRICTIONS:
    PROJECT and FOLDER types CANNOT be tagged in IDMC.
    Before calling tag_assets or untag_assets operations:
    1. Filter out any assets where type='PROJECT' or type='FOLDER'
    2. Inform the user these types were excluded from tagging
    3. Only include taggable types in the Assets parameter (DTEMPLATE, MTT, CONNECTION, DSS, etc.)

    IMPORTANT - SLACK FORMATTING:
    When responding to users about this tool, use Slack formatting (NOT Markdown):
    - Use *text* for bold (single asterisk, NOT **text**)
    - Use _text_ for italic
    - Use `code` for inline code
    - Use :emoji_name: for emojis
    """
    return "IDMC operation will be executed with real-time updates"


def _format_idmc_response(
    operation: str,
    result: Dict[str, Any],
    org_name: str,
    say_callback: Optional[Callable[[str], None]],
    logger,
    is_count_query: bool = False
) -> Dict[str, Any]:
    """
    Format IDMC response - create Excel for large datasets, tabular for small ones.

    Args:
        operation: Operation type
        result: Result from IDMC API
        org_name: Organization name
        say_callback: Slack callback
        logger: Logger instance

    Returns:
        Formatted response dict
    """
    # Operations that return object lists
    list_operations = ['get_objects', 'get_users', 'get_agents', 'get_schedules', 'get_runtime_environments']

    if operation in list_operations:
        # Determine data key based on operation
        data_key_map = {
            'get_objects': 'Objects',
            'get_users': 'Users',
            'get_agents': 'Agents',
            'get_schedules': 'Schedules',
            'get_runtime_environments': 'Environments'
        }

        data_key = data_key_map.get(operation)
        objects = result.get(data_key, [])
        count = len(objects)

        # If user just wants count, return count only
        if is_count_query:
            if say_callback:
                say_callback(f"📊 *Total count:* {count} items")
            return {
                "success": True,
                "operation": operation,
                "result": result,
                "org_name": org_name,
                "count": count,
                "count_only": True,
                "message": f"Found {count} items"
            }

        if count > 10:
            # Generate Excel report
            import pandas as pd
            import os
            from datetime import datetime

            report_dir = "Reports"
            os.makedirs(report_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"IDMCFunctionalities_{timestamp}.xlsx"
            report_path = os.path.join(report_dir, report_filename)

            # Create DataFrame and save to Excel
            df = pd.DataFrame(objects)
            df.to_excel(report_path, index=False, engine='openpyxl')

            logger.info(f"Generated Excel report: {report_path}")

            if say_callback:
                summary_msg = f"""📊 *Found {count} items*

*Report generated:* `{report_filename}`

The full data has been saved to an Excel file for easy filtering and analysis."""
                say_callback(summary_msg)

            return {
                "success": True,
                "operation": operation,
                "result": result,
                "org_name": org_name,
                "report_generated": True,
                "report_path": report_path,
                "count": count,
                "message": f"Report generated with {count} items"
            }
        else:
            # Format as table for small datasets (≤10 items)
            if count == 0:
                if say_callback:
                    say_callback(f"ℹ️ No items found for operation: *{operation}*")
            else:
                # Create tabular format
                table_msg = f"*Found {count} item(s):*\n\n"

                for idx, obj in enumerate(objects, 1):
                    table_msg += f"*{idx}. {obj.get('path', obj.get('name', 'N/A'))}*\n"

                    # Show key fields based on object type
                    if 'type' in obj:
                        table_msg += f"   • Type: `{obj['type']}`\n"
                    if 'description' in obj and obj['description']:
                        table_msg += f"   • Description: {obj['description'][:100]}\n"
                    if 'id' in obj:
                        table_msg += f"   • ID: `{obj['id']}`\n"
                    if 'updatedBy' in obj:
                        table_msg += f"   • Updated By: {obj['updatedBy']}\n"

                    table_msg += "\n"

                if say_callback:
                    say_callback(table_msg)

            return {
                "success": True,
                "operation": operation,
                "result": result,
                "org_name": org_name,
                "count": count,
                "displayed_inline": True,
                "message": f"Displayed {count} items inline"
            }
    else:
        # For other operations (create, update, delete), return as-is
        return {
            "success": True,
            "operation": operation,
            "result": result,
            "org_name": org_name,
            "message": f"Operation {operation} completed successfully"
        }


def execute_idmc_operation(
    username: str,
    password: str,
    region: str,
    operation: str,
    parameters: Dict[str, Any],
    say_callback: Optional[Callable[[str], None]] = None,
    is_count_query: bool = False
) -> Dict[str, Any]:
    """
    Execute the actual IDMC operation with step-by-step updates.

    Args:
        username: IDMC username
        password: IDMC password
        region: IDMC region
        operation: Operation to perform
        parameters: Dictionary containing operation-specific parameters
        say_callback: Optional callback function for real-time updates
        is_count_query: Set to True if user only wants count (no report generation)

    Returns:
        Dictionary containing operation results
    """
    # Initialize logger
    idmc_logger = create_idmc_logger()

    try:
        idmc_logger.info(f"Starting IDMC Operation: {operation}")
        idmc_logger.info(f"Region: {region}, Username: {username}")
        idmc_logger.info(f"Parameters: {parameters}")

        # Show configuration preview
        if say_callback:
            # Format operation name nicely
            operation_display = operation.replace('_', ' ').title()

            # Build parameters summary based on operation type
            param_summary = []
            if operation == "get_objects":
                if parameters.get("ObjectType"):
                    param_summary.append(f"Object Type: `{parameters['ObjectType']}`")
                if parameters.get("PathFilter"):
                    param_summary.append(f"Path Filter: `{parameters['PathFilter']}`")
                param_summary.append(f"Max Fetch: `{parameters.get('MaxFetch', 10000)}`")
            elif operation in ["tag_assets", "untag_assets"]:
                assets = parameters.get("Assets", [])
                param_summary.append(f"Assets: `{len(assets)}` asset(s)")
            elif operation == "create_project":
                param_summary.append(f"Project Name: `{parameters.get('ProjectName')}`")
                if parameters.get("ProjectDescription"):
                    param_summary.append(f"Description: `{parameters['ProjectDescription']}`")
            elif operation == "create_folder":
                param_summary.append(f"Folder Name: `{parameters.get('FolderName')}`")
                if parameters.get("ProjectIdentifier"):
                    param_summary.append(f"Project: `{parameters['ProjectIdentifier']}`")
            elif operation == "get_schedules":
                if parameters.get("ScheduleId"):
                    param_summary.append(f"Schedule ID: `{parameters['ScheduleId']}`")
                else:
                    param_summary.append("Fetching all schedules")
            elif operation == "get_agents":
                if parameters.get("AgentName"):
                    param_summary.append(f"Agent Name: `{parameters['AgentName']}`")
                else:
                    param_summary.append("Fetching all agents")
            elif operation == "get_users":
                param_summary.append(f"Limit: `{parameters.get('Limit', 100)}`")
            else:
                # Generic parameter display for other operations
                for key, value in parameters.items():
                    if value and not isinstance(value, (dict, list)) and len(str(value)) < 50:
                        param_summary.append(f"{key.replace('_', ' ').title()}: `{value}`")

            param_text = "\n   • ".join(param_summary) if param_summary else "No additional parameters"

            config_preview = f"""📋 *IDMC Operation Configuration:*

🎯 *Environment:*
   • Username: `{username}`
   • Password: `{'*' * 8}`
   • Region: `{region}`

⚙️  *Operation:*
   • Type: `{operation_display}`
   • {param_text}

Proceeding with operation..."""
            say_callback(config_preview)

        if say_callback:
            say_callback(f"🔧 Starting IDMC Operation: *{operation}*...")

        from IDMCFunctionalities.idmc_functions import (
            IdmcLogin, IdmcLogout, IdmcGetObjects, IdmcTagAssets, IdmcUntagAssets,
            IdmcCreateProject, IdmcUpdateProject, IdmcDeleteProject,
            IdmcCreateFolder, IdmcUpdateFolder, IdmcDeleteFolder,
            IdmcGetSchedules, IdmcCreateSchedule, IdmcUpdateSchedule, IdmcDeleteSchedule,
            IdmcGetAgents, IdmcGetAgentStatus, IdmcGetRuntimeEnvironments,
            IdmcGetUsers, IdmcCreateUser, IdmcDeleteUser,
            IdmcGetObjectPermissions, IdmcCreateObjectPermission,
            IdmcUpdateObjectPermission, IdmcDeleteObjectPermission
        )

        # Step 1: Login to IDMC
        idmc_logger.info("Step 1: Authenticating to IDMC")
        if say_callback:
            say_callback("🔐 Authenticating to IDMC...")

        login_result = IdmcLogin(username, password, region)

        if login_result["Status"] != "success":
            error_msg = f"Login failed: {login_result.get('Error', 'Unknown error')}"
            idmc_logger.error(error_msg)
            raise Exception(error_msg)

        session_id = login_result["SessionId"]
        base_api_url = login_result["BaseApiUrl"]
        org_name = login_result["OrgName"]

        idmc_logger.info(f"Successfully logged into Org: {org_name}")
        if say_callback:
            say_callback(f"✅ Logged into Org: *{org_name}*")

        # Step 2: Execute requested operation
        idmc_logger.info(f"Step 2: Executing operation: {operation}")
        if say_callback:
            say_callback(f"⚙️  Executing operation: *{operation}*...")

        result = None

        # Asset Operations
        if operation == "get_objects":
            result = IdmcGetObjects(
                session_id,
                base_api_url,
                ObjectType=parameters.get("ObjectType"),
                PathFilter=parameters.get("PathFilter"),
                QueryFilter=parameters.get("QueryFilter"),
                MaxFetch=parameters.get("MaxFetch", 10000)
            )

        elif operation == "tag_assets":
            result = IdmcTagAssets(
                session_id,
                base_api_url,
                parameters.get("Assets", [])
            )

        elif operation == "untag_assets":
            result = IdmcUntagAssets(
                session_id,
                base_api_url,
                parameters.get("Assets", [])
            )

        # Project Operations
        elif operation == "create_project":
            result = IdmcCreateProject(
                session_id,
                base_api_url,
                parameters.get("ProjectName"),
                parameters.get("ProjectDescription")
            )

        elif operation == "update_project":
            result = IdmcUpdateProject(
                session_id,
                base_api_url,
                parameters.get("ProjectIdentifier"),
                UseProjectName=parameters.get("UseProjectName", False),
                NewName=parameters.get("NewName"),
                NewDescription=parameters.get("NewDescription")
            )

        elif operation == "delete_project":
            result = IdmcDeleteProject(
                session_id,
                base_api_url,
                parameters.get("ProjectIdentifier"),
                UseProjectName=parameters.get("UseProjectName", False)
            )

        # Folder Operations
        elif operation == "create_folder":
            result = IdmcCreateFolder(
                session_id,
                base_api_url,
                parameters.get("FolderName"),
                FolderDescription=parameters.get("FolderDescription"),
                ProjectIdentifier=parameters.get("ProjectIdentifier"),
                UseProjectName=parameters.get("UseProjectName", False)
            )

        elif operation == "update_folder":
            result = IdmcUpdateFolder(
                session_id,
                base_api_url,
                parameters.get("FolderIdentifier"),
                UseFolderName=parameters.get("UseFolderName", False),
                ProjectIdentifier=parameters.get("ProjectIdentifier"),
                UseProjectName=parameters.get("UseProjectName", False),
                NewName=parameters.get("NewName"),
                NewDescription=parameters.get("NewDescription")
            )

        elif operation == "delete_folder":
            result = IdmcDeleteFolder(
                session_id,
                base_api_url,
                parameters.get("FolderIdentifier"),
                UseFolderName=parameters.get("UseFolderName", False),
                ProjectIdentifier=parameters.get("ProjectIdentifier"),
                UseProjectName=parameters.get("UseProjectName", False)
            )

        # Schedule Operations
        elif operation == "get_schedules":
            result = IdmcGetSchedules(
                session_id,
                base_api_url,
                ScheduleId=parameters.get("ScheduleId"),
                QueryFilter=parameters.get("QueryFilter")
            )

        elif operation == "create_schedule":
            result = IdmcCreateSchedule(
                session_id,
                base_api_url,
                parameters.get("ScheduleName"),
                parameters.get("StartTime"),
                parameters.get("Interval"),
                Frequency=parameters.get("Frequency"),
                Description=parameters.get("Description"),
                Status=parameters.get("Status", "enabled"),
                EndTime=parameters.get("EndTime"),
                TimeZoneId=parameters.get("TimeZoneId", "UTC"),
                DayFlags=parameters.get("DayFlags"),
                OtherParams=parameters.get("OtherParams")
            )

        elif operation == "update_schedule":
            result = IdmcUpdateSchedule(
                session_id,
                base_api_url,
                parameters.get("ScheduleId"),
                parameters.get("Updates", {})
            )

        elif operation == "delete_schedule":
            result = IdmcDeleteSchedule(
                session_id,
                base_api_url,
                parameters.get("ScheduleId")
            )

        # Agent Operations
        elif operation == "get_agents":
            result = IdmcGetAgents(
                session_id,
                base_api_url,
                AgentId=parameters.get("AgentId"),
                AgentName=parameters.get("AgentName"),
                IncludeUnassignedOnly=parameters.get("IncludeUnassignedOnly", False),
                BasicInfo=parameters.get("BasicInfo", False)
            )

        elif operation == "get_agent_status":
            result = IdmcGetAgentStatus(
                session_id,
                base_api_url,
                AgentId=parameters.get("AgentId"),
                OnlyStatus=parameters.get("OnlyStatus", True)
            )

        elif operation == "get_runtime_environments":
            result = IdmcGetRuntimeEnvironments(
                session_id,
                base_api_url,
                EnvironmentId=parameters.get("EnvironmentId"),
                EnvironmentName=parameters.get("EnvironmentName")
            )

        # User Operations
        elif operation == "get_users":
            result = IdmcGetUsers(
                session_id,
                base_api_url,
                UserId=parameters.get("UserId"),
                UserName=parameters.get("UserName"),
                Limit=parameters.get("Limit", 100),
                Skip=parameters.get("Skip", 0)
            )

        elif operation == "create_user":
            result = IdmcCreateUser(
                session_id,
                base_api_url,
                parameters.get("UserName"),
                parameters.get("FirstName"),
                parameters.get("LastName"),
                parameters.get("Email"),
                Roles=parameters.get("Roles"),
                Groups=parameters.get("Groups"),
                Password=parameters.get("Password"),
                Description=parameters.get("Description"),
                Title=parameters.get("Title"),
                Phone=parameters.get("Phone"),
                ForcePasswordChange=parameters.get("ForcePasswordChange", False),
                Authentication=parameters.get("Authentication", 0)
            )

        elif operation == "delete_user":
            result = IdmcDeleteUser(
                session_id,
                base_api_url,
                parameters.get("UserId")
            )

        else:
            raise Exception(f"Unsupported operation: {operation}")

        # Step 3: Logout
        idmc_logger.info("Step 3: Logging out from IDMC")
        IdmcLogout(session_id, base_api_url)

        # Format response based on data size
        if result and result.get("Status") == "success":
            idmc_logger.info(f"Operation completed successfully: {operation}")
            idmc_logger.info(f"Result details: {result}")
            idmc_logger.info("="*80)

            # Provide specific success message based on operation
            if operation in ["tag_assets", "untag_assets"]:
                success_count = result.get("SuccessCount", 0)
                failed_count = result.get("FailedCount", 0)
                if say_callback:
                    if failed_count > 0:
                        say_callback(f"⚠️  Partially completed: {success_count} succeeded, {failed_count} failed")
                    else:
                        say_callback(f"✅ Successfully tagged {success_count} asset(s)!")
            else:
                if say_callback:
                    say_callback(f"✅ Operation completed successfully!")

            # Check if operation returns objects/data
            formatted_response = _format_idmc_response(
                operation, result, org_name, say_callback, idmc_logger, is_count_query
            )

            return formatted_response
        else:
            error = result.get("Error", "Unknown error") if result else "No result returned"
            idmc_logger.error(f"Operation failed: {error}")
            idmc_logger.error(f"Full result: {result}")
            idmc_logger.info("="*80)
            raise Exception(error)

    except Exception as e:
        error_msg = f"❌ *IDMC Operation Failed:* {str(e)}"
        idmc_logger.error(f"IDMC operation error: {str(e)}", exc_info=True)
        idmc_logger.info("="*80)
        if say_callback:
            say_callback(error_msg)
        return {
            "success": False,
            "operation": operation,
            "message": str(e)
        }
