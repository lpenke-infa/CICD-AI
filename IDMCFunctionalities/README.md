# IDMC Operations Tool

## Overview

The IDMC Operations Tool provides direct access to IDMC (Informatica Intelligent Data Management Cloud) API operations through a conversational AI interface. It wraps 35+ IDMC API functions for managing assets, tags, projects, folders, schedules, users, agents, and permissions without requiring code knowledge.

## Module Location

```
IDMCFunctionalities/
```

## Entry Point

```
tools/idmc_tool.py → IDMCFunctionalities/idmc_functions.py
```

---

## File Structure

### 1. `__init__.py`
- **Total Lines:** 81
- **Purpose:** Package initialization and exports
- **Functions:** None (just imports)

---

### 2. `idmc_functions.py`
- **Total Lines:** 1,670
- **Purpose:** Comprehensive IDMC API wrapper with 35 functions

#### All Functions Overview

| # | Function | Line | Purpose |
|---|----------|------|---------|
| 1 | `IdmcLogin()` | 84 | Authenticate to IDMC |
| 2 | `IdmcGetObjects()` | 125 | Query IDMC objects by type/path |
| 3 | `IdmcTagAssets()` | 188 | Add tags to assets |
| 4 | `IdmcUntagAssets()` | 234 | Remove tags from assets |
| 5 | `IdmcCheckout()` | 280 | Check out assets for editing |
| 6 | `IdmcCheckin()` | 317 | Check in assets with comments |
| 7 | `IdmcUndoCheckout()` | 358 | Undo checkout operation |
| 8 | `IdmcGetOperationStatus()` | 394 | Get async operation status |
| 9 | `IdmcLogout()` | 431 | Logout from IDMC |
| 10 | `IdmcCreateProject()` | 452 | Create new project |
| 11 | `IdmcUpdateProject()` | 494 | Update project details |
| 12 | `IdmcDeleteProject()` | 538 | Delete empty project |
| 13 | `IdmcCreateFolder()` | 574 | Create new folder |
| 14 | `IdmcUpdateFolder()` | 627 | Update folder details |
| 15 | `IdmcDeleteFolder()` | 679 | Delete empty folder |
| 16 | `IdmcGetSchedules()` | 721 | Get schedule information |
| 17 | `IdmcCreateSchedule()` | 776 | Create new schedule |
| 18 | `IdmcUpdateSchedule()` | 859 | Update schedule details |
| 19 | `IdmcDeleteSchedule()` | 934 | Delete schedule |
| 20 | `IdmcGetScimTokens()` | 960 | Get SCIM tokens |
| 21 | `IdmcCreateScimToken()` | 993 | Create SCIM token |
| 22 | `IdmcDeleteScimToken()` | 1027 | Delete SCIM token |
| 23 | `IdmcGetAgents()` | 1058 | Get secure agents |
| 24 | `IdmcGetAgentStatus()` | 1115 | Get agent status |
| 25 | `IdmcGetRuntimeEnvironments()` | 1162 | Get runtime environments |
| 26 | `IdmcGetUsers()` | 1213 | Get organization users |
| 27 | `IdmcCreateUser()` | 1271 | Create new user |
| 28 | `IdmcDeleteUser()` | 1334 | Delete user |
| 29 | `IdmcGetObjectPermissions()` | 1362 | Get object permissions |
| 30 | `IdmcCreateObjectPermission()` | 1413 | Create object permission |
| 31 | `IdmcUpdateObjectPermission()` | 1481 | Update object permission |
| 32 | `IdmcDeleteObjectPermission()` | 1524 | Delete object permission |
| 33 | `IdmcExportMeteringData()` | 1562 | Export metering data |
| 34 | `IdmcGetMeteringJobStatus()` | 1610 | Get metering job status |
| 35 | `IdmcDownloadMeteringData()` | 1644 | Download metering data |

---

## Function Categories

### 🔐 Authentication (2 functions)

#### 1. `IdmcLogin(Username, Password, Region="dm-us")`

Authenticates to IDMC and returns session information.

**Parameters:**
- `Username` (str) - IDMC username
- `Password` (str) - IDMC password
- `Region` (str) - Region code (default: "dm-us")

**Returns:**
```python
{
    "Status": "success",
    "SessionId": "IDS_xxx",
    "BaseApiUrl": "https://dm-us.informaticacloud.com",
    "OrgId": "xxx",
    "OrgName": "MyOrg",
    "ServerUrl": "https://dm-us.informaticacloud.com/saas",
    "UserId": "xxx",
    "UserName": "user@example.com"
}
```

**Usage:**
```python
result = IdmcLogin("user@example.com", "password", "dm-us")
session_id = result["SessionId"]
base_url = result["BaseApiUrl"]
```

---

#### 2. `IdmcLogout(SessionId, BaseApiUrl)`

Logs out from IDMC session.

**Parameters:**
- `SessionId` (str) - Active session ID
- `BaseApiUrl` (str) - Base API URL from login

**Returns:**
```python
{"Status": "success"}
```

---

### 📦 Asset Management (5 functions)

#### 3. `IdmcGetObjects(SessionId, BaseApiUrl, ObjectType=None, PathFilter=None, MaxFetch=10000)`

Retrieves IDMC objects with optional filtering.

**Parameters:**
- `SessionId` (str) - Active session ID
- `BaseApiUrl` (str) - Base API URL
- `ObjectType` (str, optional) - Filter by type (e.g., "DTEMPLATE", "MTT", "TASKFLOW")
- `PathFilter` (str, optional) - Filter by path pattern
- `MaxFetch` (int) - Maximum objects to fetch (default: 10000)

**Supported Object Types:**
```
DTEMPLATE, MTT, TASKFLOW, DSS, DTT, DMASK, DRS, DMAPPLET, 
CONNECTION, AI_CONNECTION, AGENT, AGENTGROUP, BSERVICE, 
PROCESS, GUIDE, PROJECT, FOLDER, SCHEDULE, UDF, CLEANSE, 
PARSE, VERIFIER, DEDUPLICATE, and 45+ more types
```

**Returns:**
```python
{
    "Status": "success",
    "Objects": [
        {
            "id": "asset_id",
            "path": "Default/MyMapping",
            "type": "DTEMPLATE",
            "name": "MyMapping",
            "description": "Description",
            "updatedBy": "user@example.com",
            "updateTime": "2026-06-28T10:30:00Z"
        }
    ],
    "Count": 25
}
```

**Examples:**
```python
# Get all mappings
result = IdmcGetObjects(session_id, base_url, ObjectType="DTEMPLATE")

# Get objects in specific path
result = IdmcGetObjects(session_id, base_url, PathFilter="Default/Mappings/*")

# Get all objects
result = IdmcGetObjects(session_id, base_url)
```

---

#### 4. `IdmcCheckout(SessionId, BaseApiUrl, ObjectIds)`

Checks out assets for editing (locks them).

**Parameters:**
- `SessionId` (str) - Active session ID
- `BaseApiUrl` (str) - Base API URL
- `ObjectIds` (list) - List of object IDs to checkout

**Returns:**
```python
{
    "Status": "success",
    "CheckedOut": 5,
    "OperationId": "xxx"
}
```

---

#### 5. `IdmcCheckin(SessionId, BaseApiUrl, ObjectIds, Summary, Description=None)`

Checks in assets with comments.

**Parameters:**
- `SessionId` (str) - Active session ID
- `BaseApiUrl` (str) - Base API URL
- `ObjectIds` (list) - List of object IDs to checkin
- `Summary` (str) - Checkin summary/comment
- `Description` (str, optional) - Detailed description

---

#### 6. `IdmcUndoCheckout(SessionId, BaseApiUrl, ObjectIds)`

Undoes checkout operation (discards changes).

---

#### 7. `IdmcGetOperationStatus(SessionId, BaseApiUrl, OperationId, ExpandObjects=False)`

Gets status of asynchronous operations.

---

### 🏷️ Tag Management (2 functions)

#### 8. `IdmcTagAssets(SessionId, BaseApiUrl, Assets)`

Adds tags to assets.

**Parameters:**
- `SessionId` (str) - Active session ID
- `BaseApiUrl` (str) - Base API URL
- `Assets` (list) - List of asset dictionaries with `Id` and `Tags`

**Asset Format:**
```python
Assets = [
    {
        "Id": "asset_id_1",
        "Tags": ["Production", "Release_v1.0"]
    },
    {
        "Id": "asset_id_2",
        "Tags": ["Development", "Testing"]
    }
]
```

**Returns:**
```python
{
    "Status": "success",
    "Tagged": 2
}
```

**Usage:**
```python
assets = [
    {"Id": "abc123", "Tags": ["Production"]},
    {"Id": "def456", "Tags": ["Production", "v1.0"]}
]
result = IdmcTagAssets(session_id, base_url, assets)
```

---

#### 9. `IdmcUntagAssets(SessionId, BaseApiUrl, Assets)`

Removes tags from assets (same format as IdmcTagAssets).

---

### 📁 Project Management (3 functions)

#### 10. `IdmcCreateProject(SessionId, BaseApiUrl, ProjectName, ProjectDescription=None)`

Creates a new project.

**Parameters:**
- `SessionId` (str) - Active session ID
- `BaseApiUrl` (str) - Base API URL
- `ProjectName` (str) - Name for new project
- `ProjectDescription` (str, optional) - Project description

**Returns:**
```python
{
    "Status": "success",
    "ProjectId": "xxx",
    "ProjectName": "MyNewProject"
}
```

---

#### 11. `IdmcUpdateProject(SessionId, BaseApiUrl, ProjectIdentifier, UseProjectName=False, NewName=None, NewDescription=None)`

Updates existing project.

**Parameters:**
- `ProjectIdentifier` (str) - Project ID or name
- `UseProjectName` (bool) - True if identifier is name, False if ID
- `NewName` (str, optional) - New project name
- `NewDescription` (str, optional) - New description

---

#### 12. `IdmcDeleteProject(SessionId, BaseApiUrl, ProjectIdentifier, UseProjectName=False)`

Deletes an empty project.

**Note:** Project must be empty (no folders or assets).

---

### 📂 Folder Management (3 functions)

#### 13. `IdmcCreateFolder(SessionId, BaseApiUrl, FolderName, FolderDescription=None, ProjectIdentifier=None, UseProjectName=False)`

Creates a new folder.

**Parameters:**
- `FolderName` (str) - Name for new folder
- `FolderDescription` (str, optional) - Folder description
- `ProjectIdentifier` (str, optional) - Project ID or name
- `UseProjectName` (bool) - True if identifier is name

**Returns:**
```python
{
    "Status": "success",
    "FolderId": "xxx",
    "FolderName": "MyNewFolder"
}
```

---

#### 14. `IdmcUpdateFolder(SessionId, BaseApiUrl, FolderIdentifier, UseFolderName=False, ProjectIdentifier=None, UseProjectName=False, NewName=None, NewDescription=None)`

Updates existing folder.

---

#### 15. `IdmcDeleteFolder(SessionId, BaseApiUrl, FolderIdentifier, UseFolderName=False, ProjectIdentifier=None, UseProjectName=False)`

Deletes an empty folder.

---

### ⏰ Schedule Management (4 functions)

#### 16. `IdmcGetSchedules(SessionId, BaseApiUrl, ScheduleId=None, QueryFilter=None)`

Gets schedule information.

**Parameters:**
- `ScheduleId` (str, optional) - Specific schedule ID
- `QueryFilter` (str, optional) - Query filter string

**Returns:**
```python
{
    "Status": "success",
    "Schedules": [
        {
            "id": "schedule_id",
            "name": "Daily_Load",
            "status": "enabled",
            "frequency": "Daily",
            "startTime": "2026-06-28T02:00:00Z"
        }
    ],
    "Count": 10
}
```

---

#### 17. `IdmcCreateSchedule(SessionId, BaseApiUrl, ScheduleName, StartTime, Interval, Frequency=None, Description=None, Status="enabled", EndTime=None, TimeZoneId="UTC", DayFlags=None, OtherParams=None)`

Creates a new schedule.

**Parameters:**
- `ScheduleName` (str) - Schedule name
- `StartTime` (str) - Start time (ISO format)
- `Interval` (int) - Interval value
- `Frequency` (str) - "Daily", "Weekly", "Monthly", "Once"
- `Status` (str) - "enabled" or "disabled"
- `TimeZoneId` (str) - Timezone (default: "UTC")
- `DayFlags` (list, optional) - Days of week for weekly schedules
- `OtherParams` (dict, optional) - Additional parameters

---

#### 18. `IdmcUpdateSchedule(SessionId, BaseApiUrl, ScheduleId, Updates)`

Updates existing schedule.

**Parameters:**
- `ScheduleId` (str) - Schedule ID
- `Updates` (dict) - Dictionary with fields to update

---

#### 19. `IdmcDeleteSchedule(SessionId, BaseApiUrl, ScheduleId)`

Deletes a schedule.

---

### 🖥️ Agent Management (3 functions)

#### 23. `IdmcGetAgents(SessionId, BaseApiUrl, AgentId=None, AgentName=None, IncludeUnassignedOnly=False, BasicInfo=False)`

Gets secure agent information.

**Parameters:**
- `AgentId` (str, optional) - Specific agent ID
- `AgentName` (str, optional) - Filter by agent name
- `IncludeUnassignedOnly` (bool) - Only unassigned agents
- `BasicInfo` (bool) - Return basic info only

**Returns:**
```python
{
    "Status": "success",
    "Agents": [
        {
            "id": "agent_id",
            "name": "MySecureAgent",
            "status": "Running",
            "version": "11.8.0",
            "platform": "Linux"
        }
    ],
    "Count": 5
}
```

---

#### 24. `IdmcGetAgentStatus(SessionId, BaseApiUrl, AgentId=None, OnlyStatus=True)`

Gets agent status.

**Returns:**
```python
{
    "Status": "success",
    "AgentStatus": "Running"
}
```

---

#### 25. `IdmcGetRuntimeEnvironments(SessionId, BaseApiUrl, EnvironmentId=None, EnvironmentName=None)`

Gets runtime environment information.

**Returns:**
```python
{
    "Status": "success",
    "Environments": [
        {
            "id": "env_id",
            "name": "Production_Runtime",
            "agentCount": 3
        }
    ]
}
```

---

### 👥 User Management (3 functions)

#### 26. `IdmcGetUsers(SessionId, BaseApiUrl, UserId=None, UserName=None, Limit=100, Skip=0)`

Gets organization users.

**Parameters:**
- `UserId` (str, optional) - Specific user ID
- `UserName` (str, optional) - Filter by username
- `Limit` (int) - Max users to return (default: 100)
- `Skip` (int) - Skip first N users (pagination)

**Returns:**
```python
{
    "Status": "success",
    "Users": [
        {
            "id": "user_id",
            "name": "user@example.com",
            "firstName": "John",
            "lastName": "Doe",
            "roles": ["Designer", "Admin"]
        }
    ],
    "Count": 25
}
```

---

#### 27. `IdmcCreateUser(SessionId, BaseApiUrl, UserName, FirstName, LastName, Email, Roles=None, Groups=None, Password=None, Description=None, Title=None, Phone=None, ForcePasswordChange=False, Authentication=0)`

Creates a new user.

**Parameters:**
- `UserName` (str) - Username
- `FirstName` (str) - First name
- `LastName` (str) - Last name
- `Email` (str) - Email address
- `Roles` (list, optional) - List of role names
- `Groups` (list, optional) - List of group names
- `Password` (str, optional) - Initial password
- `ForcePasswordChange` (bool) - Force password change on first login
- `Authentication` (int) - 0=Normal, 1=SAML

---

#### 28. `IdmcDeleteUser(SessionId, BaseApiUrl, UserId)`

Deletes a user.

---

### 🔒 Permission Management (4 functions)

#### 29. `IdmcGetObjectPermissions(SessionId, BaseApiUrl, ObjectId, AclId=None)`

Gets permissions for an object.

**Returns:**
```python
{
    "Status": "success",
    "Permissions": [
        {
            "aclId": "acl_id",
            "principalType": "User",
            "principalName": "user@example.com",
            "permissions": ["Read", "Write", "Execute"]
        }
    ]
}
```

---

#### 30. `IdmcCreateObjectPermission(SessionId, BaseApiUrl, ObjectId, PrincipalType, PrincipalName, Permissions, GrantToPrincipal=True)`

Creates object permission.

**Parameters:**
- `ObjectId` (str) - Object ID
- `PrincipalType` (str) - "User" or "Group"
- `PrincipalName` (str) - User or group name
- `Permissions` (list) - List of permissions: ["Read", "Write", "Execute", "Delete"]
- `GrantToPrincipal` (bool) - Grant to principal

---

#### 31. `IdmcUpdateObjectPermission(SessionId, BaseApiUrl, ObjectId, AclId, PrincipalType, PrincipalName, Permissions)`

Updates object permission.

---

#### 32. `IdmcDeleteObjectPermission(SessionId, BaseApiUrl, ObjectId, AclId=None)`

Deletes object permission.

---

### 📊 Metering & Analytics (3 functions)

#### 33. `IdmcExportMeteringData(SessionId, BaseApiUrl, StartDate, EndDate, JobType, OrgId=None, OtherParams=None)`

Exports metering data for a date range.

---

#### 34. `IdmcGetMeteringJobStatus(SessionId, BaseApiUrl, JobId)`

Gets metering export job status.

---

#### 35. `IdmcDownloadMeteringData(SessionId, BaseApiUrl, JobId, OutputFile)`

Downloads metering data file.

---

## Usage via Slack Bot

The IDMC Operations tool is accessible through conversational AI interface.

### Example Conversations:

**Get All Mappings:**
```
User: Show me all mappings in IDMC

Bot: 🔐 Authenticating to IDMC...
     ✅ Logged into Org: MyOrg
     ⚙️  Executing operation: get_objects...
     ✅ Operation completed successfully!
     
     Found 25 mappings:
     1. Default/Customer_Mapping (DTEMPLATE)
     2. Default/Order_Mapping (DTEMPLATE)
     3. Reports/Sales_Mapping (DTEMPLATE)
     ...
```

**Create a Project:**
```
User: Create a new project called "DataMigration"

Bot: 🔐 Authenticating to IDMC...
     ✅ Logged into Org: MyOrg
     ⚙️  Executing operation: create_project...
     ✅ Operation completed successfully!
     
     Project created:
     - Name: DataMigration
     - ID: xxx
```

**Tag Assets:**
```
User: Tag asset ID abc123 with "Production" and "v1.0"

Bot: 🔐 Authenticating to IDMC...
     ✅ Logged into Org: MyOrg
     ⚙️  Executing operation: tag_assets...
     ✅ Operation completed successfully!
     
     Tagged 1 asset with 2 tags
```

**Get Agents:**
```
User: Show all secure agents

Bot: 🔐 Authenticating to IDMC...
     ✅ Logged into Org: MyOrg
     ⚙️  Executing operation: get_agents...
     ✅ Operation completed successfully!
     
     Found 3 agents:
     1. MySecureAgent - Running (v11.8.0)
     2. BackupAgent - Running (v11.7.0)
     3. TestAgent - Stopped (v11.8.0)
```

---

## Configuration

No configuration file needed! Provide credentials in conversation:

```json
{
  "username": "user@example.com",
  "password": "password",
  "region": "dm-us"
}
```

**Supported Regions:**
- `dm-us` - US Data Center
- `dm-eu` - Europe Data Center
- `dm-ap` - Asia Pacific Data Center
- `dm-em1` - EMEA Data Center

---

## Output

### Log File

**Location:**
```
Logs/IDMCFunctionalities.log
```

**Format:**
```
2026-06-28 10:39:06,503 - IDMCFunctionalities - INFO - [function:line] - Message
```

**Contents:**
- Session start/end timestamps
- Operation type and parameters
- API responses
- Success/failure status

---

### Return Object

```python
{
    "success": True,
    "operation": "get_objects",
    "result": {
        "Status": "success",
        "Objects": [...],
        "Count": 25
    },
    "org_name": "MyOrg"
}
```

---

## API Endpoints Used

The tool wraps these IDMC REST APIs:

```
# Authentication
POST /saas/public/core/v3/login
POST /saas/public/core/v3/logout

# Asset Management
GET  /public/core/v3/objects
POST /public/core/v3/checkout
POST /public/core/v3/checkin
GET  /public/core/v3/operation/{id}

# Tagging
POST /public/core/v3/tagging

# Projects & Folders
POST /public/core/v3/projects
GET  /public/core/v3/projects
PUT  /public/core/v3/projects/{id}
DELETE /public/core/v3/projects/{id}
POST /public/core/v3/folders
PUT  /public/core/v3/folders/{id}
DELETE /public/core/v3/folders/{id}

# Schedules
GET  /public/core/v3/schedule
POST /public/core/v3/schedule
PUT  /public/core/v3/schedule/{id}
DELETE /public/core/v3/schedule/{id}

# Agents
GET  /public/core/v3/agent
GET  /public/core/v3/agentgroup

# Users
GET  /public/core/v3/user
POST /public/core/v3/user
DELETE /public/core/v3/user/{id}

# Permissions
GET  /public/core/v3/acl
POST /public/core/v3/acl
PUT  /public/core/v3/acl/{id}
DELETE /public/core/v3/acl/{id}

# Metering
POST /api/v1/metering/meteringData
GET  /api/v1/metering/meteringData/{jobId}
GET  /api/v1/metering/meteringData/{jobId}/download
```

---

## IDMC Asset Type Reference

### Backend Code vs UI Display Name

Use these type codes in `ObjectType` parameter:

**General:**
- `PROJECT` - Project
- `FOLDER` - Folder

**Data Integration:**
- `DTEMPLATE` - Mapping
- `MTT` - Mapping Task
- `DSS` - Synchronization Task
- `DTT` - Data Transfer Task
- `DMASK` - Masking Task
- `DRS` - Replication Task
- `DMAPPLET` - Mapplet (Data Integration)
- `MAPPLET` - PowerCenter Mapplet
- `CONNECTION` - Connection
- `AGENT` - Secure Agent
- `AGENTGROUP` - Runtime Environment
- `BSERVICE` - Business Service Definition

**Application Integration:**
- `PROCESS` - Process
- `GUIDE` - Guide
- `AI_CONNECTION` - Application Connection
- `AI_SERVICE_CONNECTOR` - Service Connector
- `PROCESS_OBJECT` - Process Object
- `HUMAN_TASK` - Human Task

**Data Quality:**
- `CLEANSE` - Cleanse
- `DEDUPLICATE` - Deduplicate
- `DICTIONARY` - Dictionary
- `EXCEPTION` - Exception
- `LABELER` - Labeler
- `PARSE` - Parse
- `RULE_SPECIFICATION` - Rule Specification
- `VERIFIER` - Verifier
- `STRUCTURE_DISCOVERY` - Intelligent Structure Model

**Workflows:**
- `TASKFLOW` - Taskflow
- `WORKFLOW` - Linear Taskflow
- `SCHEDULE` - Schedule

**And 45+ more types...**

---

## Error Handling

All functions return consistent error format:

```python
{
    "Status": "error",
    "Error": "Descriptive error message",
    "Details": "Additional details if available"
}
```

**Common Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| Authentication failed | Invalid credentials | Verify username/password |
| Object not found | Invalid ID or path | Check object exists |
| Permission denied | Insufficient permissions | Check user roles |
| API timeout | Network issues | Retry operation |
| Invalid parameters | Missing required params | Check function signature |

---

## Statistics

| Metric | Count |
|--------|-------|
| **Total Files** | 2 |
| **Total Lines** | ~1,751 |
| **Total Functions** | 35 |
| **Function Categories** | 9 |
| **API Endpoints** | 25+ |
| **Supported Asset Types** | 70+ |
| **Execution Time** | 1-5 seconds per operation |

---

## Best Practices

### 1. Authentication
```python
# Always logout after operations
result = IdmcLogin(username, password, region)
# ... perform operations ...
IdmcLogout(result["SessionId"], result["BaseApiUrl"])
```

### 2. Error Checking
```python
result = IdmcGetObjects(session_id, base_url, ObjectType="DTEMPLATE")
if result["Status"] == "success":
    for obj in result["Objects"]:
        print(obj["name"])
else:
    print(f"Error: {result['Error']}")
```

### 3. Pagination for Large Datasets
```python
# Get users in batches
skip = 0
limit = 100
all_users = []

while True:
    result = IdmcGetUsers(session_id, base_url, Limit=limit, Skip=skip)
    if result["Status"] == "success":
        all_users.extend(result["Users"])
        if len(result["Users"]) < limit:
            break
        skip += limit
    else:
        break
```

### 4. Asset Type Filtering
```python
# Get specific asset types
mappings = IdmcGetObjects(session_id, base_url, ObjectType="DTEMPLATE")
taskflows = IdmcGetObjects(session_id, base_url, ObjectType="TASKFLOW")
connections = IdmcGetObjects(session_id, base_url, ObjectType="CONNECTION")
```

### 5. Path Filtering
```python
# Get objects in specific folders
prod_assets = IdmcGetObjects(session_id, base_url, PathFilter="Production/*")
test_assets = IdmcGetObjects(session_id, base_url, PathFilter="Testing/*")
```

---

## Use Cases

### 1. Asset Inventory
Get complete inventory of all assets:
```
User: Show me all assets in IDMC
```

### 2. Tag Management
Bulk tag assets for release:
```
User: Tag all mappings with "Release_v2.0"
```

### 3. Project Setup
Create project structure:
```
User: Create project "CustomerData" with folders "Mappings" and "Connections"
```

### 4. Agent Monitoring
Check agent health:
```
User: Show status of all secure agents
```

### 5. User Management
List users and roles:
```
User: Show all users in the organization
```

### 6. Schedule Management
View scheduled tasks:
```
User: Show all enabled schedules
```

### 7. Permission Audit
Review object permissions:
```
User: Show permissions for mapping "Customer_Load"
```

---

## Integration

### With CICD Migration

IDMC Operations can be used alongside CICD migration:
- **Before Migration:** Check asset status, verify connections
- **After Migration:** Verify assets, apply additional tags
- **Monitoring:** Check agent status, view schedules

### With Monitoring Systems

Export data for external monitoring:
```python
# Get all assets and export to monitoring system
result = IdmcGetObjects(session_id, base_url)
if result["Status"] == "success":
    export_to_monitoring(result["Objects"])
```

### With Automation Scripts

Use in Python scripts:
```python
from IDMC.idmc_functions import IdmcLogin, IdmcGetObjects, IdmcTagAssets

# Login
login = IdmcLogin("user@example.com", "password", "dm-us")
session_id = login["SessionId"]
base_url = login["BaseApiUrl"]

# Get and tag assets
objects = IdmcGetObjects(session_id, base_url, ObjectType="DTEMPLATE")
assets_to_tag = [
    {"Id": obj["id"], "Tags": ["Production"]}
    for obj in objects["Objects"]
]
IdmcTagAssets(session_id, base_url, assets_to_tag)
```

---

## Troubleshooting

### Issue: Authentication Timeout

**Cause:** Network latency to IDMC

**Solution:**
- Check network connectivity
- Verify region code is correct
- Try different region if multi-region org

### Issue: Object Not Found

**Cause:** Invalid object ID or path

**Solution:**
- Use `IdmcGetObjects()` to find correct ID
- Verify object exists in IDMC UI
- Check path spelling (case-sensitive)

### Issue: Permission Denied

**Cause:** User lacks required permissions

**Solution:**
- Check user roles in IDMC
- Request admin to grant permissions
- Use different user with appropriate roles

### Issue: Rate Limiting

**Cause:** Too many API calls

**Solution:**
- Add delays between operations
- Batch operations when possible
- Use pagination for large datasets

---

## Advanced Features

### Complex Queries

Filter objects with path patterns:
```python
# Get all mappings in Production folder and subfolders
result = IdmcGetObjects(
    session_id, 
    base_url, 
    ObjectType="DTEMPLATE",
    PathFilter="Production/**"
)
```

### Bulk Operations

Tag multiple assets at once:
```python
assets = [
    {"Id": "id1", "Tags": ["Tag1", "Tag2"]},
    {"Id": "id2", "Tags": ["Tag1", "Tag3"]},
    {"Id": "id3", "Tags": ["Tag2", "Tag3"]}
]
IdmcTagAssets(session_id, base_url, assets)
```

### Async Operations

Check long-running operation status:
```python
# Start operation
checkout_result = IdmcCheckout(session_id, base_url, object_ids)
op_id = checkout_result["OperationId"]

# Poll status
status = IdmcGetOperationStatus(session_id, base_url, op_id)
```

---

## Naming Conventions

All IDMC functions follow PascalCase:
- `IdmcLogin` not `idmc_login`
- `IdmcGetObjects` not `idmc_get_objects`
- `IdmcTagAssets` not `idmc_tag_assets`

All parameters use PascalCase:
- `SessionId` not `session_id`
- `BaseApiUrl` not `base_api_url`
- `ObjectType` not `object_type`

This matches IDMC API naming conventions.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-06-28 | Initial release with 35 functions |
| 1.1 | 2026-06-28 | Added logging with IDMCFunctionalities.log |
| 1.2 | 2026-06-28 | Integrated with Slack bot for conversational access |

---

## Support

For issues or questions:
1. Check logs in `Logs/IDMCFunctionalities.log`
2. Verify IDMC credentials and region
3. Check IDMC API documentation for specific operations
4. Contact IDMC administrator for permissions issues

---

## Quick Reference

### Most Common Operations

```python
# Login
login = IdmcLogin(username, password, region)

# Get all mappings
mappings = IdmcGetObjects(session_id, base_url, ObjectType="DTEMPLATE")

# Tag assets
IdmcTagAssets(session_id, base_url, [{"Id": "xxx", "Tags": ["Production"]}])

# Create project
IdmcCreateProject(session_id, base_url, "MyProject", "Description")

# Get agents
agents = IdmcGetAgents(session_id, base_url)

# Get users
users = IdmcGetUsers(session_id, base_url, Limit=100)

# Logout
IdmcLogout(session_id, base_url)
```

---

**This tool provides complete IDMC control through conversational AI!** 🚀
