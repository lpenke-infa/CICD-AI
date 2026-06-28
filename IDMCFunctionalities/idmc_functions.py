"""
IDMC Functions - Simple generic API wrapper
One function to get all objects, AI analyzes the results
All variables use PascalCase naming convention
"""

# =============================================================================
# IDMC ASSET TYPE REFERENCE - Backend Code vs UI Display Name
# Use this reference when working with IDMC objects
# =============================================================================
#
# GENERAL TYPES:
#   PROJECT                    - Project
#   FOLDER                     - Folder
#
# DATA INTEGRATION TYPES:
#   DTEMPLATE                  - Mapping
#   MTT                        - Mapping Task
#   DSS                        - Synchronization Task
#   DTT                        - Data Transfer Task
#   DMASK                      - Masking Task
#   DRS                        - Replication Task
#   DMAPPLET                   - Mapplet (Data Integration)
#   MAPPLET                    - PowerCenter Mapplet
#   CONNECTION                 - Connection
#   AGENT                      - Secure Agent
#   AGENTGROUP                 - Runtime Environment
#   BSERVICE                   - Business Service Definition
#   HSCHEMA                    - Hierarchical Schema
#   PCS                        - PowerCenter Task
#   FWCONFIG                   - Fixed Width Configuration
#   CUSTOMSOURCE               - Saved Query
#   MI_FILE_LISTENER           - File Listener
#   MI_TASK                    - File Ingestion and Replication
#   DBMI_TASK                  - Database Ingestion and Replication
#   APPMI_TASK                 - Application Ingestion and Replication
#   WORKFLOW                   - Linear Taskflow
#   SCHEDULE                   - Schedule
#   SCHEDULE_JOB               - Schedule Job
#   SCHEDULE_BLACKOUT          - Schedule Blackout Period
#   TASKFLOW                   - Taskflow
#   UDF                        - User-Defined Function
#
# APPLICATION INTEGRATION TYPES:
#   PROCESS                    - Process
#   GUIDE                      - Guide
#   AI_CONNECTION              - Application Connection
#   AI_SERVICE_CONNECTOR       - Service Connector
#   PROCESS_OBJECT             - Process Object
#   HUMAN_TASK                 - Human Task
#
# DATA QUALITY TYPES:
#   CLEANSE                    - Cleanse
#   DEDUPLICATE                - Deduplicate
#   DICTIONARY                 - Dictionary
#   EXCEPTION                  - Exception
#   LABELER                    - Labeler
#   PARSE                      - Parse
#   RULE_SPECIFICATION         - Rule Specification
#   VERIFIER                   - Verifier
#   STRUCTURE_DISCOVERY        - Intelligent Structure Model
#
# B2B GATEWAY TYPES:
#   B2BGW_MONITOR              - B2B Gateway Monitor
#   B2BGW_CUSTOMER             - B2B Gateway Customer
#   B2BGW_SUPPLIER             - B2B Gateway Supplier
#
# Note: Object types are case-insensitive in API calls
# =============================================================================

import requests
import json
import logging

logging.basicConfig(level=logging.WARNING)


# =============================================================================
# FUNCTION: IdmcLogin
# PURPOSE: Authenticate to IDMC
# INPUTS: Username, Password, Region (default: "dm-us")
# RETURNS: dict with Status, SessionId, BaseApiUrl, OrgId, OrgName, Error
# =============================================================================
def IdmcLogin(Username, Password, Region="dm-us"):
    """Login to IDMC"""
    try:
        BaseUrl = f"https://{Region}.informaticacloud.com"
        Endpoint = f"{BaseUrl}/saas/public/core/v3/login"

        Response = requests.post(
            Endpoint,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json={"username": Username, "password": Password},
            timeout=30
        )
        Response.raise_for_status()
        Data = Response.json()

        UserInfo = Data.get('userInfo', {})
        Products = Data.get('products', [])
        BaseApiUrl = Products[0].get('baseApiUrl') if Products else None

        return {
            "Status": "success",
            "SessionId": UserInfo.get('sessionId'),
            "BaseApiUrl": BaseApiUrl,
            "OrgId": UserInfo.get('orgId'),
            "OrgName": UserInfo.get('orgName')
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcGetObjects
# PURPOSE: Generic function to fetch objects from IDMC
# INPUTS:
#   - SessionId (str): Session ID from login
#   - BaseApiUrl (str): Base API URL from login
#   - ObjectType (str): Optional - 'DTEMPLATE', 'PROJECT', etc. (None = all objects)
#   - PathFilter (str): Optional - filter by path (client-side filter)
#   - QueryFilter (str): Optional - API query filter (e.g., "tags contains 'MyTag'")
#   - MaxFetch (int): Max objects to fetch (default 10000)
# RETURNS: dict with Status, Count, Objects[], Error
# EXAMPLES:
#   - Get all mappings: IdmcGetObjects(..., ObjectType="DTEMPLATE")
#   - Get assets in folder: IdmcGetObjects(..., QueryFilter="path=='Project/Folder'")
#   - Get assets with tag: IdmcGetObjects(..., QueryFilter="tags contains 'Production'")
#   - Combined filters: IdmcGetObjects(..., QueryFilter="type=='MTT' and tags contains 'Dev'")
# =============================================================================
def IdmcGetObjects(SessionId, BaseApiUrl, ObjectType=None, PathFilter=None, QueryFilter=None, MaxFetch=10000):
    """Generic function to get objects from IDMC"""
    try:
        # Build query - priority: QueryFilter > ObjectType
        if QueryFilter:
            # Use custom query filter
            import urllib.parse
            EncodedQuery = urllib.parse.quote(QueryFilter)
            Endpoint = f"{BaseApiUrl}/public/core/v3/objects?q={EncodedQuery}"
        elif ObjectType:
            Endpoint = f"{BaseApiUrl}/public/core/v3/objects?q=type=='{ObjectType}'"
        else:
            Endpoint = f"{BaseApiUrl}/public/core/v3/objects"

        Headers = {
            "Content-Type": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        AllObjects = []
        Offset = 0
        Limit = 200

        while Offset < MaxFetch:
            # Add pagination parameters properly (use 'skip' not 'offset')
            Separator = '&' if '?' in Endpoint else '?'
            Url = f"{Endpoint}{Separator}skip={Offset}&limit={Limit}"
            Response = requests.get(Url, headers=Headers, timeout=60)
            Response.raise_for_status()

            Data = Response.json()
            Objects = Data.get('objects', [])
            if not Objects:
                break

            # Apply path filter if specified (client-side filtering)
            if PathFilter:
                Filtered = []
                for Obj in Objects:
                    ObjPath = Obj.get('path', '')
                    if ObjPath == PathFilter or ObjPath.startswith(PathFilter + '/'):
                        Filtered.append(Obj)
                AllObjects.extend(Filtered)
            else:
                AllObjects.extend(Objects)

            if len(Objects) < Limit:
                break
            Offset += Limit

        return {
            "Status": "success",
            "Count": len(AllObjects),
            "Objects": AllObjects
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcTagAssets
# PURPOSE: Add tags to assets (max 100 per call)
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - Assets (list): [{"id": "...", "tags": ["tag1", "tag2"]}, ...]
# RETURNS: dict with Status, SuccessCount, FailedCount, Results[], Error
# =============================================================================
def IdmcTagAssets(SessionId, BaseApiUrl, Assets):
    """Tag assets"""
    try:
        if len(Assets) > 100:
            Assets = Assets[:100]

        Endpoint = f"{BaseApiUrl}/public/core/v3/TagObjects"
        Headers = {
            "Content-Type": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.post(Endpoint, headers=Headers, json=Assets, timeout=60)

        # Handle 204 No Content (success)
        if Response.status_code == 204:
            return {
                "Status": "success",
                "SuccessCount": len(Assets),
                "FailedCount": 0,
                "Message": f"Successfully tagged {len(Assets)} asset(s)"
            }

        # Handle other success responses
        if Response.status_code >= 200 and Response.status_code < 300:
            try:
                Results = Response.json()
                if isinstance(Results, list):
                    SuccessCount = sum(1 for R in Results if R.get('status') == 'SUCCESS')
                    FailedCount = len(Results) - SuccessCount

                    return {
                        "Status": "success",
                        "SuccessCount": SuccessCount,
                        "FailedCount": FailedCount,
                        "Results": Results,
                        "Message": f"Tagged {SuccessCount}/{len(Results)} asset(s) successfully"
                    }
                else:
                    return {
                        "Status": "success",
                        "SuccessCount": len(Assets),
                        "FailedCount": 0,
                        "Message": "Tagging completed successfully"
                    }
            except:
                # Response is success but not JSON (rare case)
                return {
                    "Status": "success",
                    "SuccessCount": len(Assets),
                    "FailedCount": 0,
                    "Message": "Tagging completed successfully"
                }

        # Handle error responses
        Response.raise_for_status()

    except requests.exceptions.HTTPError as HttpError:
        # Detailed HTTP error logging
        ErrorMessage = f"HTTP {Response.status_code}: {Response.text[:500]}"
        return {"Status": "failed", "Error": ErrorMessage}
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcUntagAssets
# PURPOSE: Remove tags from assets (max 100 per call)
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - Assets (list): [{"id": "...", "tags": ["tag1", "tag2"]}, ...]
# RETURNS: dict with Status, SuccessCount, FailedCount, Results[], Error
# =============================================================================
def IdmcUntagAssets(SessionId, BaseApiUrl, Assets):
    """Untag assets (remove tags)"""
    try:
        if len(Assets) > 100:
            Assets = Assets[:100]

        Endpoint = f"{BaseApiUrl}/public/core/v3/UntagObjects"
        Headers = {
            "Content-Type": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.post(Endpoint, headers=Headers, json=Assets, timeout=60)

        if Response.status_code == 204:
            return {
                "Status": "success",
                "SuccessCount": len(Assets),
                "FailedCount": 0
            }

        Response.raise_for_status()
        Results = Response.json()

        SuccessCount = sum(1 for R in Results if R.get('status') == 'SUCCESS')
        FailedCount = len(Results) - SuccessCount

        return {
            "Status": "partial" if FailedCount > 0 else "success",
            "SuccessCount": SuccessCount,
            "FailedCount": FailedCount,
            "Results": Results
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcCheckout
# PURPOSE: Checkout objects for editing (locks them)
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ObjectIds (list): List of object IDs to checkout
# RETURNS: dict with Status, OperationId, Error
# =============================================================================
def IdmcCheckout(SessionId, BaseApiUrl, ObjectIds):
    """Checkout objects"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/checkout"
        Headers = {
            "Content-Type": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Objects = [{"id": ObjId} for ObjId in ObjectIds]
        Payload = {"objects": Objects}

        Response = requests.post(Endpoint, headers=Headers, json=Payload, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        return {
            "Status": "success",
            "OperationId": Data.get('id'),
            "State": Data.get('status', {}).get('state'),
            "Message": Data.get('status', {}).get('message')
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcCheckin
# PURPOSE: Checkin objects to repository
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ObjectIds (list): List of object IDs to checkin
#   - Summary (str): Commit message (max 255 chars)
#   - Description (str): Optional detailed description
# RETURNS: dict with Status, OperationId, Error
# =============================================================================
def IdmcCheckin(SessionId, BaseApiUrl, ObjectIds, Summary, Description=None):
    """Checkin objects"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/checkin"
        Headers = {
            "Content-Type": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Objects = [{"id": ObjId} for ObjId in ObjectIds]
        Payload = {
            "objects": Objects,
            "summary": Summary
        }

        if Description:
            Payload["description"] = Description

        Response = requests.post(Endpoint, headers=Headers, json=Payload, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        return {
            "Status": "success",
            "OperationId": Data.get('id'),
            "State": Data.get('status', {}).get('state'),
            "Message": Data.get('status', {}).get('message')
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcUndoCheckout
# PURPOSE: Undo checkout and revert to last pulled version
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ObjectIds (list): List of object IDs to undo checkout
# RETURNS: dict with Status, OperationId, Error
# =============================================================================
def IdmcUndoCheckout(SessionId, BaseApiUrl, ObjectIds):
    """Undo checkout"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/undoCheckout"
        Headers = {
            "Content-Type": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Objects = [{"id": ObjId} for ObjId in ObjectIds]
        Payload = {"objects": Objects}

        Response = requests.post(Endpoint, headers=Headers, json=Payload, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        return {
            "Status": "success",
            "OperationId": Data.get('id'),
            "State": Data.get('status', {}).get('state'),
            "Message": Data.get('status', {}).get('message')
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcGetOperationStatus
# PURPOSE: Get status of source control operation
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - OperationId (str): Operation ID from checkout/checkin/undo
#   - ExpandObjects (bool): Include object-level details (default: False)
# RETURNS: dict with Status, Action, State, Objects, Error
# =============================================================================
def IdmcGetOperationStatus(SessionId, BaseApiUrl, OperationId, ExpandObjects=False):
    """Get source control operation status"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/sourceControlAction/{OperationId}"
        if ExpandObjects:
            Endpoint += "?expand=objects"

        Headers = {
            "Content-Type": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.get(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        return {
            "Status": "success",
            "OperationId": Data.get('id'),
            "Action": Data.get('action'),
            "State": Data.get('status', {}).get('state'),
            "Message": Data.get('status', {}).get('message'),
            "CommitHash": Data.get('commitHash'),
            "StartTime": Data.get('startTime'),
            "EndTime": Data.get('endTime'),
            "Objects": Data.get('objects', [])
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcLogout
# PURPOSE: Logout from IDMC
# INPUTS: SessionId, BaseApiUrl
# RETURNS: dict with Status
# =============================================================================
def IdmcLogout(SessionId, BaseApiUrl):
    """Logout"""
    try:
        Endpoint = f"{BaseApiUrl}/api/v2/logout"
        Headers = {"Content-Type": "application/json", "icSessionId": SessionId}
        requests.post(Endpoint, headers=Headers, timeout=10)
        return {"Status": "success"}
    except:
        return {"Status": "success"}


# =============================================================================
# FUNCTION: IdmcCreateProject
# PURPOSE: Create a new project
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ProjectName (str): Name of the project
#   - ProjectDescription (str): Optional description
# RETURNS: dict with Status, ProjectId, ProjectName, UpdatedBy, UpdateTime, Error
# =============================================================================
def IdmcCreateProject(SessionId, BaseApiUrl, ProjectName, ProjectDescription=None):
    """Create a new project"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/projects"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Payload = {"name": ProjectName}
        if ProjectDescription:
            Payload["description"] = ProjectDescription

        Response = requests.post(Endpoint, headers=Headers, json=Payload, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        return {
            "Status": "success",
            "ProjectId": Data.get('id'),
            "ProjectName": Data.get('name'),
            "Description": Data.get('description'),
            "UpdatedBy": Data.get('updatedBy'),
            "UpdateTime": Data.get('updateTime')
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcUpdateProject
# PURPOSE: Update project name or description
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ProjectIdentifier (str): Project ID or project name
#   - UseProjectName (bool): True if ProjectIdentifier is a name, False if ID
#   - NewName (str): Optional new project name
#   - NewDescription (str): Optional new description
# RETURNS: dict with Status, Error
# =============================================================================
def IdmcUpdateProject(SessionId, BaseApiUrl, ProjectIdentifier, UseProjectName=False, NewName=None, NewDescription=None):
    """Update project"""
    try:
        if UseProjectName:
            import urllib.parse
            EncodedName = urllib.parse.quote(ProjectIdentifier)
            Endpoint = f"{BaseApiUrl}/public/core/v3/projects/name/{EncodedName}"
        else:
            Endpoint = f"{BaseApiUrl}/public/core/v3/projects/{ProjectIdentifier}"

        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Payload = {}
        if NewName:
            Payload["name"] = NewName
        if NewDescription:
            Payload["description"] = NewDescription

        if not Payload:
            return {"Status": "failed", "Error": "No update parameters provided"}

        Response = requests.patch(Endpoint, headers=Headers, json=Payload, timeout=60)
        Response.raise_for_status()

        return {"Status": "success"}
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcDeleteProject
# PURPOSE: Delete an empty project
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ProjectIdentifier (str): Project ID or project name
#   - UseProjectName (bool): True if ProjectIdentifier is a name, False if ID
# RETURNS: dict with Status, Error
# NOTE: Project must be empty (no folders or assets)
# =============================================================================
def IdmcDeleteProject(SessionId, BaseApiUrl, ProjectIdentifier, UseProjectName=False):
    """Delete an empty project"""
    try:
        if UseProjectName:
            import urllib.parse
            EncodedName = urllib.parse.quote(ProjectIdentifier)
            Endpoint = f"{BaseApiUrl}/public/core/v3/projects/name/{EncodedName}"
        else:
            Endpoint = f"{BaseApiUrl}/public/core/v3/projects/{ProjectIdentifier}"

        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.delete(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()

        return {"Status": "success"}
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcCreateFolder
# PURPOSE: Create a new folder in a project
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - FolderName (str): Name of the folder
#   - FolderDescription (str): Optional description
#   - ProjectIdentifier (str): Optional project ID or name (uses Default if None)
#   - UseProjectName (bool): True if ProjectIdentifier is a name, False if ID
# RETURNS: dict with Status, FolderId, FolderName, UpdatedBy, UpdateTime, Error
# =============================================================================
def IdmcCreateFolder(SessionId, BaseApiUrl, FolderName, FolderDescription=None, ProjectIdentifier=None, UseProjectName=False):
    """Create a new folder"""
    try:
        if ProjectIdentifier:
            if UseProjectName:
                import urllib.parse
                EncodedName = urllib.parse.quote(ProjectIdentifier)
                Endpoint = f"{BaseApiUrl}/public/core/v3/projects/name/{EncodedName}/folders"
            else:
                Endpoint = f"{BaseApiUrl}/public/core/v3/projects/{ProjectIdentifier}/folders"
        else:
            Endpoint = f"{BaseApiUrl}/public/core/v3/folders"

        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Payload = {"name": FolderName}
        if FolderDescription:
            Payload["description"] = FolderDescription

        Response = requests.post(Endpoint, headers=Headers, json=Payload, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        return {
            "Status": "success",
            "FolderId": Data.get('id'),
            "FolderName": Data.get('name'),
            "Description": Data.get('description'),
            "UpdatedBy": Data.get('updatedBy'),
            "UpdateTime": Data.get('updateTime')
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcUpdateFolder
# PURPOSE: Update folder name or description
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - FolderIdentifier (str): Folder ID or folder name
#   - UseFolderName (bool): True if FolderIdentifier is a name, False if ID
#   - ProjectIdentifier (str): Optional project ID or name (for Default project)
#   - UseProjectName (bool): True if ProjectIdentifier is a name, False if ID
#   - NewName (str): Optional new folder name
#   - NewDescription (str): Optional new description
# RETURNS: dict with Status, Error
# =============================================================================
def IdmcUpdateFolder(SessionId, BaseApiUrl, FolderIdentifier, UseFolderName=False, ProjectIdentifier=None, UseProjectName=False, NewName=None, NewDescription=None):
    """Update folder"""
    try:
        if ProjectIdentifier:
            if UseProjectName and UseFolderName:
                import urllib.parse
                EncodedProject = urllib.parse.quote(ProjectIdentifier)
                EncodedFolder = urllib.parse.quote(FolderIdentifier)
                Endpoint = f"{BaseApiUrl}/public/core/v3/projects/name/{EncodedProject}/folders/name/{EncodedFolder}"
            elif not UseProjectName and not UseFolderName:
                Endpoint = f"{BaseApiUrl}/public/core/v3/projects/{ProjectIdentifier}/folders/{FolderIdentifier}"
            else:
                return {"Status": "failed", "Error": "Cannot mix IDs and names in URI"}
        else:
            Endpoint = f"{BaseApiUrl}/public/core/v3/folders/{FolderIdentifier}"

        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Payload = {}
        if NewName:
            Payload["name"] = NewName
        if NewDescription:
            Payload["description"] = NewDescription

        if not Payload:
            return {"Status": "failed", "Error": "No update parameters provided"}

        Response = requests.patch(Endpoint, headers=Headers, json=Payload, timeout=60)
        Response.raise_for_status()

        return {"Status": "success"}
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcDeleteFolder
# PURPOSE: Delete an empty folder
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - FolderIdentifier (str): Folder ID or folder name
#   - UseFolderName (bool): True if FolderIdentifier is a name, False if ID
#   - ProjectIdentifier (str): Optional project ID or name
#   - UseProjectName (bool): True if ProjectIdentifier is a name, False if ID
# RETURNS: dict with Status, Error
# NOTE: Folder must be empty (no assets)
# =============================================================================
def IdmcDeleteFolder(SessionId, BaseApiUrl, FolderIdentifier, UseFolderName=False, ProjectIdentifier=None, UseProjectName=False):
    """Delete an empty folder"""
    try:
        if ProjectIdentifier:
            if UseProjectName and UseFolderName:
                import urllib.parse
                EncodedProject = urllib.parse.quote(ProjectIdentifier)
                EncodedFolder = urllib.parse.quote(FolderIdentifier)
                Endpoint = f"{BaseApiUrl}/public/core/v3/projects/name/{EncodedProject}/folders/name/{EncodedFolder}"
            elif not UseProjectName and not UseFolderName:
                Endpoint = f"{BaseApiUrl}/public/core/v3/projects/{ProjectIdentifier}/folders/{FolderIdentifier}"
            else:
                return {"Status": "failed", "Error": "Cannot mix IDs and names in URI"}
        else:
            if UseFolderName:
                return {"Status": "failed", "Error": "Folder name requires project context"}
            Endpoint = f"{BaseApiUrl}/public/core/v3/folders/{FolderIdentifier}"

        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.delete(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()

        return {"Status": "success"}
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcGetSchedules
# PURPOSE: Get schedules from IDMC
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ScheduleId (str): Optional specific schedule ID
#   - QueryFilter (str): Optional query filter (e.g., "status=='enabled'")
# RETURNS: dict with Status, Count, Schedules[], Error
# =============================================================================
def IdmcGetSchedules(SessionId, BaseApiUrl, ScheduleId=None, QueryFilter=None):
    """Get schedules"""
    try:
        if ScheduleId:
            Endpoint = f"{BaseApiUrl}/public/core/v3/schedule/{ScheduleId}"
        else:
            Endpoint = f"{BaseApiUrl}/public/core/v3/schedule"
            if QueryFilter:
                Endpoint += f"?q={QueryFilter}"

        Headers = {
            "Content-Type": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.get(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        # Single schedule vs list
        if ScheduleId:
            return {
                "Status": "success",
                "Schedule": Data
            }
        else:
            Schedules = Data if isinstance(Data, list) else [Data]
            return {
                "Status": "success",
                "Count": len(Schedules),
                "Schedules": Schedules
            }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcCreateSchedule
# PURPOSE: Create a new schedule
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ScheduleName (str): Schedule name
#   - StartTime (str): Start time in UTC ISO format (e.g., "2024-09-18T22:00:00.000Z")
#   - Interval (str): None, Minutely, Hourly, Daily, Weekly, Biweekly, Monthly
#   - Frequency (int): Optional repeat frequency (depends on interval)
#   - Description (str): Optional description
#   - Status (str): Optional "enabled" or "disabled" (default: enabled)
#   - EndTime (str): Optional end time in UTC ISO format
#   - TimeZoneId (str): Optional timezone (default: UTC)
#   - DayFlags (dict): Optional {"sun": True, "mon": False, ...}
#   - OtherParams (dict): Optional additional parameters (dayOfMonth, weekDay, etc.)
# RETURNS: dict with Status, ScheduleId, Schedule object, Error
# NOTE: IDMC requires all day flags and certain fields to be explicitly set
# =============================================================================
def IdmcCreateSchedule(SessionId, BaseApiUrl, ScheduleName, StartTime, Interval,
                       Frequency=None, Description=None, Status="enabled",
                       EndTime=None, TimeZoneId="UTC", DayFlags=None, OtherParams=None):
    """Create a schedule"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/schedule"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        # Base payload with required fields
        Payload = {
            "name": ScheduleName,
            "startTime": StartTime,
            "interval": Interval,
            "status": Status,
            "timeZoneId": TimeZoneId,
            # IDMC requires these fields to be explicitly set
            "rangeStartTime": None,
            "rangeEndTime": None,
            "endTime": EndTime,
            "weekDay": False,
            "dayOfMonth": 0,
            "weekOfMonth": None,
            "dayOfWeek": None
        }

        # Set default day flags (all False if not provided)
        DefaultDayFlags = {
            "sun": False,
            "mon": False,
            "tue": False,
            "wed": False,
            "thu": False,
            "fri": False,
            "sat": False
        }

        if DayFlags:
            DefaultDayFlags.update(DayFlags)
        Payload.update(DefaultDayFlags)

        # Add optional parameters
        if Description:
            Payload["description"] = Description
        if Frequency is not None:
            Payload["frequency"] = Frequency
        if OtherParams:
            Payload.update(OtherParams)

        Response = requests.post(Endpoint, headers=Headers, json=Payload, timeout=60)

        if Response.status_code >= 400:
            try:
                ErrorData = Response.json()
                return {"Status": "failed", "Error": f"{Response.status_code}: {ErrorData}"}
            except:
                return {"Status": "failed", "Error": f"{Response.status_code}: {Response.text}"}

        Response.raise_for_status()
        Data = Response.json()

        return {
            "Status": "success",
            "ScheduleId": Data.get('id'),
            "Schedule": Data
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcUpdateSchedule
# PURPOSE: Update an existing schedule
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ScheduleId (str): Schedule ID to update
#   - Updates (dict): Dictionary of fields to update (name, status, interval, etc.)
# RETURNS: dict with Status, Error
# =============================================================================
def IdmcUpdateSchedule(SessionId, BaseApiUrl, ScheduleId, Updates):
    """Update a schedule"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/schedule/{ScheduleId}"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        if not Updates:
            return {"Status": "failed", "Error": "No update parameters provided"}

        # Always include id and scheduleFederatedId (get from current schedule first)
        GetResult = IdmcGetSchedules(SessionId, BaseApiUrl, ScheduleId=ScheduleId)
        if GetResult["Status"] != "success":
            return {"Status": "failed", "Error": "Could not retrieve schedule for update"}

        CurrentSchedule = GetResult["Schedule"]

        # Build complete payload with all current values plus updates
        Payload = {
            "id": CurrentSchedule.get("id"),
            "scheduleFederatedId": CurrentSchedule.get("scheduleFederatedId"),
            "name": CurrentSchedule.get("name"),
            "startTime": CurrentSchedule.get("startTime"),
            "interval": CurrentSchedule.get("interval"),
            "status": CurrentSchedule.get("status"),
            "frequency": CurrentSchedule.get("frequency"),
            "mon": CurrentSchedule.get("mon"),
            "tue": CurrentSchedule.get("tue"),
            "wed": CurrentSchedule.get("wed"),
            "thu": CurrentSchedule.get("thu"),
            "fri": CurrentSchedule.get("fri"),
            "sat": CurrentSchedule.get("sat"),
            "sun": CurrentSchedule.get("sun"),
            "weekDay": CurrentSchedule.get("weekDay"),
            "dayOfMonth": CurrentSchedule.get("dayOfMonth"),
            "weekOfMonth": CurrentSchedule.get("weekOfMonth"),
            "dayOfWeek": CurrentSchedule.get("dayOfWeek"),
            "timeZoneId": CurrentSchedule.get("timeZoneId"),
            "rangeStartTime": CurrentSchedule.get("rangeStartTime"),
            "rangeEndTime": CurrentSchedule.get("rangeEndTime"),
            "endTime": CurrentSchedule.get("endTime"),
            "description": CurrentSchedule.get("description")
        }

        # Apply updates
        Payload.update(Updates)

        Response = requests.patch(Endpoint, headers=Headers, json=Payload, timeout=60)

        if Response.status_code >= 400:
            try:
                ErrorData = Response.json()
                return {"Status": "failed", "Error": f"{Response.status_code}: {ErrorData}"}
            except:
                return {"Status": "failed", "Error": f"{Response.status_code}: {Response.text}"}

        Response.raise_for_status()

        return {"Status": "success"}
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcDeleteSchedule
# PURPOSE: Delete a schedule
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ScheduleId (str): Schedule ID to delete
# RETURNS: dict with Status, Error
# =============================================================================
def IdmcDeleteSchedule(SessionId, BaseApiUrl, ScheduleId):
    """Delete a schedule"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/schedule/{ScheduleId}"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.delete(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()

        return {"Status": "success"}
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcGetScimTokens
# PURPOSE: Get all SCIM tokens for the organization
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
# RETURNS: dict with Status, Count, Tokens[], Error
# =============================================================================
def IdmcGetScimTokens(SessionId, BaseApiUrl):
    """Get SCIM tokens"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/scimTokens"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.get(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        Tokens = Data if isinstance(Data, list) else [Data]
        return {
            "Status": "success",
            "Count": len(Tokens),
            "Tokens": Tokens
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcCreateScimToken
# PURPOSE: Create a new SCIM token
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
# RETURNS: dict with Status, TokenId, TokenValue, Expiry, TokenStatus, Error
# NOTE: Maximum 2 tokens per organization. Must delete existing token if limit reached.
# =============================================================================
def IdmcCreateScimToken(SessionId, BaseApiUrl):
    """Create a SCIM token"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/scimTokens"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.post(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        return {
            "Status": "success",
            "TokenId": Data.get('id'),
            "TokenValue": Data.get('value'),
            "Expiry": Data.get('expiry'),
            "TokenStatus": Data.get('status')
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcDeleteScimToken
# PURPOSE: Delete a SCIM token
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - TokenId (str): Token ID to delete
# RETURNS: dict with Status, Error
# =============================================================================
def IdmcDeleteScimToken(SessionId, BaseApiUrl, TokenId):
    """Delete a SCIM token"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/scimTokens/{TokenId}"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.delete(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()

        return {"Status": "success"}
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcGetAgents
# PURPOSE: Get all secure agents in the organization
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - AgentId (str): Optional specific agent ID
#   - AgentName (str): Optional agent name
#   - IncludeUnassignedOnly (bool): Optional - return only unassigned agents
#   - BasicInfo (bool): Optional - include package and configuration details
# RETURNS: dict with Status, Count, Agents[], Error
# NOTE: Uses v2 API with icSessionId header
# =============================================================================
def IdmcGetAgents(SessionId, BaseApiUrl, AgentId=None, AgentName=None, IncludeUnassignedOnly=False, BasicInfo=False):
    """Get secure agents"""
    try:
        if AgentId:
            Endpoint = f"{BaseApiUrl}/api/v2/agent/{AgentId}"
        elif AgentName:
            import urllib.parse
            EncodedName = urllib.parse.quote(AgentName)
            Endpoint = f"{BaseApiUrl}/api/v2/agent/name/{EncodedName}"
        else:
            Endpoint = f"{BaseApiUrl}/api/v2/agent"
            Params = []
            if IncludeUnassignedOnly:
                Params.append("includeUnassignedOnly=true")
            if BasicInfo:
                Params.append("basicInfo=true")
            if Params:
                Endpoint += "?" + "&".join(Params)

        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "icSessionId": SessionId
        }

        Response = requests.get(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        # Single agent vs list
        if AgentId or AgentName:
            return {
                "Status": "success",
                "Agent": Data
            }
        else:
            Agents = Data if isinstance(Data, list) else [Data]
            return {
                "Status": "success",
                "Count": len(Agents),
                "Agents": Agents
            }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcGetAgentStatus
# PURPOSE: Get service status for agents
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - AgentId (str): Optional specific agent ID
#   - OnlyStatus (bool): Optional - if False, includes agent details (default: True)
# RETURNS: dict with Status, AgentStatus or AgentsStatus[], Error
# NOTE: Uses v2 API with icSessionId header
# =============================================================================
def IdmcGetAgentStatus(SessionId, BaseApiUrl, AgentId=None, OnlyStatus=True):
    """Get agent service status"""
    try:
        if AgentId:
            Endpoint = f"{BaseApiUrl}/api/v2/agent/details/{AgentId}"
        else:
            Endpoint = f"{BaseApiUrl}/api/v2/agent/details"

        if not OnlyStatus:
            Endpoint += "?onlyStatus=false"

        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "icSessionId": SessionId
        }

        Response = requests.get(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        if AgentId:
            return {
                "Status": "success",
                "AgentStatus": Data
            }
        else:
            return {
                "Status": "success",
                "Count": len(Data) if isinstance(Data, list) else 1,
                "AgentsStatus": Data if isinstance(Data, list) else [Data]
            }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcGetRuntimeEnvironments
# PURPOSE: Get runtime environments (agent groups)
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - EnvironmentId (str): Optional specific runtime environment ID
#   - EnvironmentName (str): Optional runtime environment name
# RETURNS: dict with Status, Count, Environments[], Error
# NOTE: Uses v2 API with icSessionId header
# =============================================================================
def IdmcGetRuntimeEnvironments(SessionId, BaseApiUrl, EnvironmentId=None, EnvironmentName=None):
    """Get runtime environments (agent groups)"""
    try:
        if EnvironmentId:
            Endpoint = f"{BaseApiUrl}/api/v2/runtimeEnvironment/{EnvironmentId}"
        elif EnvironmentName:
            import urllib.parse
            EncodedName = urllib.parse.quote(EnvironmentName)
            Endpoint = f"{BaseApiUrl}/api/v2/runtimeEnvironment/name/{EncodedName}"
        else:
            Endpoint = f"{BaseApiUrl}/api/v2/runtimeEnvironment"

        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "icSessionId": SessionId
        }

        Response = requests.get(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        # Single environment vs list
        if EnvironmentId or EnvironmentName:
            return {
                "Status": "success",
                "Environment": Data
            }
        else:
            Environments = Data if isinstance(Data, list) else [Data]
            return {
                "Status": "success",
                "Count": len(Environments),
                "Environments": Environments
            }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcGetUsers
# PURPOSE: Get users in the organization
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - UserId (str): Optional specific user ID
#   - UserName (str): Optional user name
#   - Limit (int): Max users to return (default: 100, max: 200)
#   - Skip (int): Pagination offset (default: 0)
# RETURNS: dict with Status, Count, Users[], Error
# =============================================================================
def IdmcGetUsers(SessionId, BaseApiUrl, UserId=None, UserName=None, Limit=100, Skip=0):
    """Get users"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/users"

        Params = []
        if UserId:
            Params.append(f"q=userId=={UserId}")
        elif UserName:
            Params.append(f"q=userName=={UserName}")

        Params.append(f"limit={Limit}")
        Params.append(f"skip={Skip}")

        if Params:
            Endpoint += "?" + "&".join(Params)

        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.get(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        Users = Data if isinstance(Data, list) else [Data]
        return {
            "Status": "success",
            "Count": len(Users),
            "Users": Users
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcCreateUser
# PURPOSE: Create a new user
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - UserName (str): User name (email or alphanumeric)
#   - FirstName (str): First name
#   - LastName (str): Last name
#   - Email (str): Email address
#   - Roles (list): Optional list of role IDs
#   - Groups (list): Optional list of group IDs
#   - Password (str): Optional password (if empty, activation email sent)
#   - Description (str): Optional description
#   - Title (str): Optional job title
#   - Phone (str): Optional phone number
#   - ForcePasswordChange (bool): Optional require password reset (default: False)
#   - Authentication (int): Optional 0=Native, 1=SAML (default: 0)
# RETURNS: dict with Status, UserId, User object, Error
# NOTE: Must specify Roles or Groups (or both)
# =============================================================================
def IdmcCreateUser(SessionId, BaseApiUrl, UserName, FirstName, LastName, Email,
                   Roles=None, Groups=None, Password=None, Description=None,
                   Title=None, Phone=None, ForcePasswordChange=False, Authentication=0):
    """Create a user"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/users"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Payload = {
            "name": UserName,
            "firstName": FirstName,
            "lastName": LastName,
            "email": Email,
            "authentication": Authentication,
            "forcePasswordChange": ForcePasswordChange
        }

        # Must have roles or groups
        if Roles:
            Payload["roles"] = Roles
        if Groups:
            Payload["groups"] = Groups

        if not Roles and not Groups:
            return {"Status": "failed", "Error": "Must specify Roles or Groups"}

        # Optional fields
        if Password:
            Payload["password"] = Password
        if Description:
            Payload["description"] = Description
        if Title:
            Payload["title"] = Title
        if Phone:
            Payload["phone"] = Phone

        Response = requests.post(Endpoint, headers=Headers, json=Payload, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        return {
            "Status": "success",
            "UserId": Data.get('id'),
            "User": Data
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcDeleteUser
# PURPOSE: Delete a user
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - UserId (str): User ID to delete
# RETURNS: dict with Status, Error
# NOTE: Requires administrator privileges
# =============================================================================
def IdmcDeleteUser(SessionId, BaseApiUrl, UserId):
    """Delete a user"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/users/{UserId}"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.delete(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()

        return {"Status": "success"}
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcGetObjectPermissions
# PURPOSE: Get permissions for an object
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ObjectId (str): Object ID
#   - AclId (str): Optional specific ACL ID
# RETURNS: dict with Status, Permissions[], Error
# =============================================================================
def IdmcGetObjectPermissions(SessionId, BaseApiUrl, ObjectId, AclId=None):
    """Get object permissions"""
    try:
        if AclId:
            Endpoint = f"{BaseApiUrl}/public/core/v3/objects/{ObjectId}/permissions/{AclId}"
        else:
            Endpoint = f"{BaseApiUrl}/public/core/v3/objects/{ObjectId}/permissions"

        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.get(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        # Single ACL vs list
        if AclId:
            return {
                "Status": "success",
                "Permission": Data
            }
        else:
            Permissions = Data if isinstance(Data, list) else [Data]
            return {
                "Status": "success",
                "Count": len(Permissions),
                "Permissions": Permissions
            }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcCreateObjectPermission
# PURPOSE: Create permission (ACL) for an object
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ObjectId (str): Object ID
#   - PrincipalType (str): "USER" or "GROUP"
#   - PrincipalName (str): Username or group name
#   - Read (bool): Read permission
#   - Update (bool): Update permission
#   - Delete (bool): Delete permission
#   - Execute (bool): Execute permission
#   - ChangePermission (bool): Change permission permission
# RETURNS: dict with Status, AclId, Permission object, Error
# =============================================================================
def IdmcCreateObjectPermission(SessionId, BaseApiUrl, ObjectId, PrincipalType, PrincipalName,
                                Read=False, Update=False, Delete=False, Execute=False, ChangePermission=False):
    """Create object permission"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/objects/{ObjectId}/permissions"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Payload = {
            "principal": {
                "type": PrincipalType,
                "name": PrincipalName
            },
            "permissions": {
                "read": Read,
                "update": Update,
                "delete": Delete,
                "execute": Execute,
                "changePermission": ChangePermission
            }
        }

        Response = requests.post(Endpoint, headers=Headers, json=Payload, timeout=60)
        Response.raise_for_status()

        # API may return 204 or actual data
        if Response.status_code == 204:
            return {
                "Status": "success",
                "AclId": None,
                "Permission": None
            }

        Data = Response.json()

        # Handle both single object and list responses
        if isinstance(Data, list) and len(Data) > 0:
            Data = Data[0]

        return {
            "Status": "success",
            "AclId": Data.get('id') if isinstance(Data, dict) else None,
            "Permission": Data
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcUpdateObjectPermission
# PURPOSE: Update permission (ACL) for an object
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ObjectId (str): Object ID
#   - AclId (str): ACL ID to update
#   - PrincipalType (str): "USER" or "GROUP"
#   - PrincipalName (str): Username or group name
#   - Read (bool): Read permission
#   - Update (bool): Update permission
#   - Delete (bool): Delete permission
#   - Execute (bool): Execute permission
#   - ChangePermission (bool): Change permission permission
# RETURNS: dict with Status, Error
# =============================================================================
def IdmcUpdateObjectPermission(SessionId, BaseApiUrl, ObjectId, AclId, PrincipalType, PrincipalName,
                                Read=False, Update=False, Delete=False, Execute=False, ChangePermission=False):
    """Update object permission"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/objects/{ObjectId}/permissions/{AclId}"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Payload = {
            "principal": {
                "type": PrincipalType,
                "name": PrincipalName
            },
            "permissions": {
                "read": Read,
                "update": Update,
                "delete": Delete,
                "execute": Execute,
                "changePermission": ChangePermission
            }
        }

        Response = requests.put(Endpoint, headers=Headers, json=Payload, timeout=60)
        Response.raise_for_status()

        return {"Status": "success"}
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcDeleteObjectPermission
# PURPOSE: Delete permission(s) for an object
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - ObjectId (str): Object ID
#   - AclId (str): Optional ACL ID (if None, deletes all permissions)
# RETURNS: dict with Status, Error
# =============================================================================
def IdmcDeleteObjectPermission(SessionId, BaseApiUrl, ObjectId, AclId=None):
    """Delete object permission(s)"""
    try:
        if AclId:
            Endpoint = f"{BaseApiUrl}/public/core/v3/objects/{ObjectId}/permissions/{AclId}"
        else:
            Endpoint = f"{BaseApiUrl}/public/core/v3/objects/{ObjectId}/permissions"

        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.delete(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()

        return {"Status": "success"}
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcExportMeteringData
# PURPOSE: Request export of metering data
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - StartDate (str): Start date in ISO 8601 format (e.g., "2024-08-12T00:00:00Z")
#   - EndDate (str): End date in ISO 8601 format (max 30-day range)
#   - JobType (str): "PROJECT_FOLDER", "ASSET", or "JOB"
#   - CombinedMeterUsage (str): Optional "TRUE" or "FALSE" (default: "FALSE")
#   - AllLinkedOrgs (str): Optional "TRUE" or "FALSE" (default: "FALSE")
#   - MeterId (str): Optional meter ID (for asset/job level)
#   - CallbackUrl (str): Optional callback URL for status updates
# RETURNS: dict with Status, JobId, JobDetails, Error
# NOTE: Max 30-day date range, max 5 active jobs per org
# =============================================================================
def IdmcExportMeteringData(SessionId, BaseApiUrl, StartDate, EndDate, JobType,
                           CombinedMeterUsage="FALSE", AllLinkedOrgs="FALSE",
                           MeterId=None, CallbackUrl=None):
    """Export metering data"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/license/metering/ExportMeteringData"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Payload = {
            "startDate": StartDate,
            "endDate": EndDate,
            "jobType": JobType,
            "combinedMeterUsage": CombinedMeterUsage,
            "allLinkedOrgs": AllLinkedOrgs
        }

        if MeterId:
            Payload["meterId"] = MeterId
        if CallbackUrl:
            Payload["callbackUrl"] = CallbackUrl

        Response = requests.post(Endpoint, headers=Headers, json=Payload, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        return {
            "Status": "success",
            "JobId": Data.get('jobId'),
            "JobDetails": Data
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcGetMeteringJobStatus
# PURPOSE: Get status of metering data export job
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - JobId (str): Export job ID
# RETURNS: dict with Status, JobStatus, JobDetails, Error
# NOTE: JobStatus values: CREATED, PROCESSING, SUCCESS, FAILED, PARTIAL_SUCCESS
# =============================================================================
def IdmcGetMeteringJobStatus(SessionId, BaseApiUrl, JobId):
    """Get metering export job status"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/license/metering/ExportMeteringData/{JobId}"
        Headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.get(Endpoint, headers=Headers, timeout=60)
        Response.raise_for_status()
        Data = Response.json()

        return {
            "Status": "success",
            "JobStatus": Data.get('status'),
            "JobDetails": Data
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# FUNCTION: IdmcDownloadMeteringData
# PURPOSE: Download metering data file (ZIP)
# INPUTS:
#   - SessionId (str): Session ID
#   - BaseApiUrl (str): Base API URL
#   - JobId (str): Export job ID
#   - OutputFile (str): Local file path to save the ZIP file
# RETURNS: dict with Status, FilePath, Error
# NOTE: Job must have status SUCCESS or PARTIAL_SUCCESS
# =============================================================================
def IdmcDownloadMeteringData(SessionId, BaseApiUrl, JobId, OutputFile):
    """Download metering data file"""
    try:
        Endpoint = f"{BaseApiUrl}/public/core/v3/license/metering/ExportMeteringData/{JobId}/download"
        Headers = {
            "INFA-SESSION-ID": SessionId
        }

        Response = requests.get(Endpoint, headers=Headers, timeout=120, stream=True)
        Response.raise_for_status()

        with open(OutputFile, 'wb') as F:
            for Chunk in Response.iter_content(chunk_size=8192):
                F.write(Chunk)

        return {
            "Status": "success",
            "FilePath": OutputFile
        }
    except Exception as Error:
        return {"Status": "failed", "Error": str(Error)}


# =============================================================================
# NOTE: For testing and orchestration, use main.py
# This file contains only generic reusable functions
# =============================================================================
