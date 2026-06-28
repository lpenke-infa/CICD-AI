# CICD Migration Tool

## Overview

The CICD Migration Tool is the core component that automates the migration of IICS assets from a source environment to a target environment using Git as the transport mechanism. It handles authentication, asset retrieval, Git operations, project/folder creation, asset import, and post-migration tagging in an 8-step automated workflow.

## Module Location

```
CICDMigration/
```

## Entry Point

```
tools/cicd_tool.py → CICDMigration/main.py
```

---

## File Structure

### 1. `__init__.py`
- **Total Lines:** 27
- **Purpose:** Package initialization and exports
- **Functions:** None (just imports and __all__ definition)

---

### 2. `cherrypick.py`
- **Total Lines:** 268
- **Purpose:** Git operations for asset migration

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `run_git_command()` | 19 | ~48 | Executes Git commands with error handling and logging |
| `git_config()` | 67 | ~61 | Configures Git repository (clone/pull, set credentials) |
| `git_operations()` | 128 | ~102 | Performs cherry-pick operations between branches |
| `cherrypick()` | 230 | ~38 | Main entry point for Git-based asset migration |

**Git Workflow:**
1. Clone/pull repository
2. Configure Git user credentials
3. Checkout source branch
4. Checkout target branch
5. Cherry-pick commits with asset changes
6. Push to remote target branch
7. Return commit hash

---

### 3. `config.py`
- **Total Lines:** 39
- **Purpose:** Configuration constants and asset type mappings

#### Constants

```python
# API Configuration
API_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2
PULL_STATUS_CHECK_INTERVAL = 15
TAG_BATCH_SIZE = 100

# Asset Type Extensions (24+ types)
TYPE_EXTENSIONS = {
    "DTEMPLATE": [["dtemplate.xml"], ["dtemplate.xml", "zip"]],
    "MTT": [["mtt.xml"], ["mtt.xml", "zip"]],
    "TASKFLOW": [["taskflow.xml"], ["taskflow.xml", "zip"]],
    # ... 20+ more types
}
```

**Supported Asset Types:**
- Data Integration: DTEMPLATE, MTT, DSS, DTT, DMASK, DRS
- Taskflows: TASKFLOW, WORKFLOW
- Connections: AI_CONNECTION, CONNECTION
- Business Services: BSERVICE, PROCESS
- Data Quality: CLEANSE, PARSE, VERIFIER, DEDUPLICATE
- And 15+ more types

---

### 4. `createProjectsAndFolders.py`
- **Total Lines:** 307
- **Purpose:** Creates required project and folder structure in target environment

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `extract_folder_and_project()` | 16 | ~36 | Extracts unique project/folder combinations from assets |
| `is_project_or_folder_exists()` | 52 | ~34 | Checks if project or folder exists in target |
| `create_project()` | 86 | ~59 | Creates a new project in target IICS |
| `get_project_id()` | 145 | ~44 | Retrieves project ID by name |
| `create_folder()` | 189 | ~57 | Creates a new folder in target IICS |
| `create_projects_and_folders()` | 246 | ~61 | Main entry point - creates all required projects and folders |

**API Endpoints:**
```
POST /public/core/v3/projects       - Create project
GET  /public/core/v3/projects       - List projects
GET  /public/core/v3/projects/{id}  - Get project details
POST /public/core/v3/folders        - Create folder
```

---

### 5. `database.py`
- **Total Lines:** 104
- **Purpose:** Records migration audit trail in SQL Server database

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `add_record()` | 15 | ~89 | Inserts migration record into database (optional) |

**Database Schema:**
```sql
CREATE TABLE dbo.Deployment_Details (
    ProjectName VARCHAR(255),
    IICSSourceOrg VARCHAR(255),
    IICSSourceOrgID VARCHAR(255),
    CommitHash VARCHAR(255),
    Tag VARCHAR(255),
    Deployment_Date DATE,
    Rollback_Date DATE,
    IICSTargetOrgID VARCHAR(255),
    IICSTargetOrg VARCHAR(255),
    AssetsMigrated INT
);
```

**Note:** Database logging is optional and requires pymssql package.

---

### 6. `logger.py`
- **Total Lines:** 59
- **Purpose:** Logging configuration for CICD operations

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `create_logger()` | 9 | ~50 | Creates and configures logger with file and console handlers |

**Log Format:**
```
2026-06-28 10:39:06,503 - CICDMigration - INFO - [function:line] - Message
```

**Log File:**
```
Logs/CICDMigration.log  (append mode)
```

---

### 7. `login.py`
- **Total Lines:** 79
- **Purpose:** IICS authentication

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `login()` | 11 | ~56 | Authenticates to IICS and returns session data |
| `iics_login()` | 67 | ~12 | Alias for backward compatibility |

**Returns:**
```python
{
    'sessionId': 'xxx',
    'baseApiUrl': 'https://dm-us.informaticacloud.com',
    'orgId': 'xxx',
    'orgName': 'MyOrg'
}
```

---

### 8. `main.py` ⭐ (Core Orchestrator)
- **Total Lines:** 218
- **Purpose:** Main orchestration of 8-step migration workflow

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `load_configuration()` | 27 | ~25 | Loads and parses configuration JSON file |
| `run_migration()` | 52 | ~144 | **Main workflow** - Orchestrates all 8 migration steps |
| `main()` | 196 | ~22 | Command-line entry point |

---

### 9. `postMigrationTag.py`
- **Total Lines:** 204
- **Purpose:** Applies tags to migrated assets in target environment

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `lookup_v3()` | 16 | ~72 | Looks up asset IDs in target environment by path |
| `post_migration_tagging_v3()` | 88 | ~73 | Applies tags to assets in batches |
| `post_migration_tag()` | 161 | ~43 | Main entry point for post-migration tagging |

**Tagging Strategy:**
- Batch processing (100 assets per batch)
- Retry logic for failed tags
- Validates asset existence before tagging

**API Endpoints:**
```
POST /public/core/v3/lookup  - Lookup asset IDs
POST /public/core/v3/tagging - Apply tags
```

---

### 10. `pull.py`
- **Total Lines:** 213
- **Purpose:** Imports assets from Git to target IICS environment

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `pull_v3()` | 17 | ~77 | Initiates pull operation from Git commit |
| `get_pull_status_v3()` | 94 | ~77 | Polls pull operation status until completion |
| `pull_assets()` | 171 | ~42 | Main entry point for asset pull operations |

**Pull Workflow:**
1. Initiate pull from specific Git commit
2. Poll status every 15 seconds
3. Wait for completion (can take several minutes)
4. Validate success

**API Endpoints:**
```
POST /public/core/v3/commit/pull          - Initiate pull
GET  /public/core/v3/commit/pull/{taskId} - Check status
```

---

### 11. `taggedAssets.py`
- **Total Lines:** 228
- **Purpose:** Retrieves tagged assets from source environment

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `generate_git_path()` | 16 | ~34 | Generates Git file paths for asset types |
| `retrieve_tagged_assets()` | 50 | ~50 | Retrieves assets with specified tags from IICS |
| `filter_and_parse_path()` | 100 | ~62 | Filters assets by project and parses metadata |
| `tagged_assets()` | 162 | ~66 | Main entry point - gets tagged assets with Git paths |

**Returns:**
```python
git_paths = [
    "Explore/Default/MyMapping.dtemplate.xml",
    "Explore/Default/MyMapping.dtemplate.xml.zip"
]

asset_metadata = [
    {
        'id': 'asset_id',
        'path': 'Default/MyMapping',
        'type': 'DTEMPLATE',
        'name': 'MyMapping',
        'project': 'MyProject',
        'folder': 'Default'
    }
]
```

---

### 12. `utils.py`
- **Total Lines:** 116
- **Purpose:** Utility functions for retry logic and validation

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `retry_with_backoff()` | 10 | ~36 | Decorator for retry with exponential backoff |
| `sanitize_for_log()` | 46 | ~26 | Sanitizes sensitive data (passwords) for logging |
| `validate_input_data()` | 72 | ~44 | Validates all required configuration fields |

**Retry Configuration:**
- Max retries: 3
- Backoff factor: 2 (1s, 2s, 4s)
- Applies to all API calls

---

## 8-Step Migration Workflow

### Step 1: Authenticate to Source IICS 🔐
- Logs into source IICS environment
- Retrieves session ID and API URL
- Validates credentials and connectivity

**Input:** Source username, password, region  
**Output:** Session data with orgId, orgName

---

### Step 2: Retrieve Tagged Assets 🏷️
- Queries IICS API for assets with pre-migration tags
- Filters by specified project
- Generates Git file paths for each asset type
- Returns asset metadata and Git paths

**Input:** Session ID, tags, project name  
**Output:** List of assets with Git paths

**Example:**
```
Found 25 assets to migrate:
- Default/Customer_Mapping (DTEMPLATE)
- Default/Load_Taskflow (TASKFLOW)
- Connections/Salesforce_Conn (AI_CONNECTION)
```

---

### Step 3: Authenticate to Target IICS 🔐
- Logs into target IICS environment
- Retrieves session ID and API URL
- Validates target environment access

**Input:** Target username, password, region  
**Output:** Session data with orgId, orgName

---

### Step 4: Create Projects and Folders 📁
- Extracts unique project/folder combinations from assets
- Checks if projects exist in target
- Creates missing projects
- Creates missing folders within projects
- Maintains folder hierarchy

**Input:** Asset metadata, target session  
**Output:** All required projects and folders created

**Example:**
```
Creating structure:
- Project: MyProject
  └─ Folder: Default
     └─ Folder: Mappings
```

---

### Step 5: Cherry-pick Assets via Git 🌿
- Clones/pulls Git repository
- Configures Git credentials
- Checks out source branch (e.g., DEV)
- Checks out target branch (e.g., QA)
- Cherry-picks commits with asset changes
- Pushes to remote target branch
- Returns commit hash

**Input:** Git config, asset Git paths  
**Output:** Commit hash for pull operation

**Git Commands:**
```bash
git clone <repo>
git config user.name / user.email
git checkout <source-branch>
git checkout <target-branch>
git cherry-pick <commit>
git push origin <target-branch>
```

---

### Step 6: Pull Assets to Target Environment ⬇️
- Initiates pull operation from specific commit
- Polls status every 15 seconds
- Waits for completion (can take minutes)
- Validates all assets imported successfully

**Input:** Commit hash, target session  
**Output:** Assets imported to target IICS

**Status Flow:**
```
RUNNING → RUNNING → RUNNING → SUCCESS
```

---

### Step 7: Apply Post-Migration Tags 🏷️
- Looks up asset IDs in target environment
- Applies post-migration tags in batches (100 per batch)
- Retries failed tags
- Validates tagging completion

**Input:** Asset metadata, tags, target session  
**Output:** All assets tagged in target

**Example Tags:** "Migrated", "Release_v1.0", "Production"

---

### Step 8: Record in Database 💾
- Inserts migration record into audit database
- Records source/target org details
- Stores commit hash for rollback
- Logs asset count and timestamp

**Input:** Migration metadata  
**Output:** Database record (optional)

**Note:** Database step is optional and will continue on failure.

---

## Configuration

### Required Fields

```json
{
  "ProjectName": ["MyProject"],
  
  "IICS_SRC_username": "source_user@example.com",
  "IICS_SRC_password": "source_password",
  "IICS_SRC_region": "dm-us",
  
  "IICS_TGT_username": "target_user@example.com",
  "IICS_TGT_password": "target_password",
  "IICS_TGT_region": "dm-us",
  
  "PreMigration_Tag": ["PreMigration", "ReadyToMigrate"],
  "PostMigration_Tag": ["Migrated"],
  
  "Git_Repository_URL": "https://github.com/org/repo.git",
  "Git_config_useremail": "user@example.com",
  "Git_config_username": "Your Name",
  "Git_password": "git_personal_access_token",
  
  "Git_SRC_Branch": "DEV",
  "Git_TGT_Branch": "QA",
  
  "Publish": 0,
  "logFileDir": "Logs"
}
```

### Configuration Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `ProjectName` | Array | IICS project name(s) | `["MyProject"]` |
| `IICS_SRC_username` | String | Source IICS username | `"user@example.com"` |
| `IICS_SRC_password` | String | Source IICS password | `"password123"` |
| `IICS_SRC_region` | String | Source region | `"dm-us"`, `"dm-eu"`, `"dm-ap"` |
| `IICS_TGT_username` | String | Target IICS username | `"user@example.com"` |
| `IICS_TGT_password` | String | Target IICS password | `"password123"` |
| `IICS_TGT_region` | String | Target region | `"dm-us"`, `"dm-eu"`, `"dm-ap"` |
| `PreMigration_Tag` | Array | Tags to filter source assets | `["Tag1", "Tag2"]` |
| `PostMigration_Tag` | Array | Tags to apply in target | `["Migrated"]` |
| `Git_Repository_URL` | String | Git repository URL | `"https://github.com/..."` |
| `Git_config_useremail` | String | Git commit email | `"user@example.com"` |
| `Git_config_username` | String | Git commit username | `"John Doe"` |
| `Git_password` | String | Git personal access token | `"ghp_xxxxx"` |
| `Git_SRC_Branch` | String | Source branch name | `"DEV"`, `"develop"` |
| `Git_TGT_Branch` | String | Target branch name | `"QA"`, `"staging"` |
| `Publish` | Integer | Publish assets (0=no, 1=yes) | `0` |
| `logFileDir` | String | Log directory | `"Logs"` |

---

## Output

### Log File

**Location:**
```
Logs/CICDMigration.log
```

**Format:**
```
2026-06-28 10:39:06,503 - CICDMigration - INFO - [function:line] - Message
```

**Contents:**
- Session start/end timestamps
- Each step with detailed progress
- Asset counts and details
- Git operations and commit hashes
- API responses and errors
- Timing information

---

### Return Object

```python
{
    "success": True,
    "message": "Migration completed successfully",
    "assets_migrated": 25,
    "source_org": "MySourceOrg",
    "target_org": "MyTargetOrg",
    "commit_hash": "abc1234567890def"
}
```

**Failure Response:**
```python
{
    "success": False,
    "message": "Error message details",
    "assets_migrated": 0,
    "source_org": None,
    "target_org": None,
    "commit_hash": None
}
```

---

## Usage

### Via Slack Bot (Recommended)

```
User: Run CICD migration with config file demo_migration.json

Bot: 🚀 Starting CI/CD Migration Process...
     
     🔐 Step 1/8: Authenticating to Source IICS...
     ✅ Logged into Source Org: MySourceOrg
     
     🏷️  Step 2/8: Retrieving Tagged Assets from Source...
     ✅ Found 25 assets to migrate
     
     🔐 Step 3/8: Authenticating to Target IICS...
     ✅ Logged into Target Org: MyTargetOrg
     
     📁 Step 4/8: Creating Required Projects and Folders...
     ✅ Projects and folders verified/created successfully
     
     🌿 Step 5/8: Cherry-picking Assets via Git...
     ✅ Git operations complete. Commit: abc12345
     
     ⬇️  Step 6/8: Pulling Assets to Target Environment...
     ✅ Assets pulled successfully to MyTargetOrg
     
     🏷️  Step 7/8: Applying Post-Migration Tags...
     ✅ Tagged 25 assets with Migrated
     
     💾 Step 8/8: Recording Migration in Database...
     ✅ Database record created
     
     🎉 MIGRATION COMPLETED SUCCESSFULLY!
     
     📊 Summary:
        • Assets Migrated: 25
        • Source Org: MySourceOrg
        • Target Org: MyTargetOrg
        • Commit Hash: abc1234567890def
     
     Would you like to run Post-Migration Validation?
     Reply with "yes" to proceed.
```

### Via Python

```python
from CICD.main import run_migration

result = run_migration('path/to/config.json')

if result['success']:
    print(f"✅ {result['assets_migrated']} assets migrated")
    print(f"📊 {result['source_org']} → {result['target_org']}")
    print(f"🔗 Commit: {result['commit_hash']}")
else:
    print(f"❌ Migration failed: {result['message']}")
```

### Via Command Line

```bash
python CICDMigration/main.py path/to/config.json
```

---

## Complete Migration Flow

```
Pre-Migration Check (Validate readiness)
    ↓
Review & Fix Issues
    ↓
CICD Migration (8 Steps) ← YOU ARE HERE
    ↓
Post-Migration Check (Verify success)
    ↓
User Acceptance Testing
```

---

## Error Handling

### Exception Handling

The CICD module uses standard Python `Exception` class for all error handling, maintaining consistency with Pre-Migration and Post-Migration modules.

**Example:**
```python
try:
    result = run_git_command(cmd)
except Exception as e:
    logger.error(f"Git operation failed: {str(e)}")
    raise Exception(f"Git operation failed: {str(e)}") from e
```

All exceptions include:
- Descriptive error messages
- Original exception chaining (using `from e`)
- Full stack traces in logs
- Context about which operation failed

### Retry Logic

All API calls use exponential backoff with 3 retries:
- Retry 1: Wait 1 second
- Retry 2: Wait 2 seconds  
- Retry 3: Wait 4 seconds

Applies to:
- IICS API calls (login, asset retrieval, pull, tagging)
- Git operations (clone, push, cherry-pick)

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| No assets found | No assets with pre-migration tags | Run pre-migration check first |
| Authentication failed | Invalid credentials | Verify username/password/region |
| Git clone failed | Invalid repo URL or token | Check Git_Repository_URL and Git_password |
| Cherry-pick failed | Conflicting changes | Manually resolve Git conflicts |
| Pull operation failed | Invalid commit or permissions | Verify commit hash and permissions |
| Tagging failed | Assets not found in target | Check pull operation succeeded |
| Project creation failed | Duplicate project name | Check if project already exists |

### Rollback

If migration fails:
1. Check logs for failure point
2. Target environment may have partial migration
3. Use commit hash for rollback if needed
4. Re-run after fixing issues

---

## Dependencies

```python
import sys
import json
import traceback
import os
import subprocess
import shutil
import time
from typing import Dict, List, Tuple
from datetime import datetime
import requests
import pymssql  # Optional for database logging
```

**Required Packages:**
- `requests` - IICS API calls
- `pymssql` - Database logging (optional)
- `git` - Git command-line tool must be installed

**System Requirements:**
- Git installed and accessible in PATH
- Network access to IICS and Git repository
- Write permissions for local Git operations

---

## Statistics

| Metric | Count |
|--------|-------|
| **Total Files** | 12 |
| **Total Lines** | ~1,918 |
| **Total Functions** | 31 |
| **Total Classes** | 0 (uses standard exceptions) |
| **Migration Steps** | 8 |
| **API Endpoints** | ~10 |
| **Supported Asset Types** | 24+ |
| **Avg Execution Time** | 5-15 minutes |

---

## Best Practices

### Before Migration

1. ✅ **Run Pre-Migration Check** - Identify issues
2. ✅ **Review asset list** - Verify correct assets tagged
3. ✅ **Check connections** - Ensure available in target
4. ✅ **Backup target** - In case rollback needed
5. ✅ **Test Git access** - Verify credentials work
6. ✅ **Verify branches exist** - Source and target branches

### During Migration

1. ✅ **Monitor progress** - Watch real-time updates
2. ✅ **Check logs** - Review for warnings
3. ✅ **Don't interrupt** - Let migration complete
4. ✅ **Note commit hash** - For rollback if needed

### After Migration

1. ✅ **Run Post-Migration Check** - Verify success
2. ✅ **Compare asset counts** - Pre vs Post
3. ✅ **Test key assets** - Validate functionality
4. ✅ **Review tags** - Confirm post-migration tags applied
5. ✅ **Keep reports** - Historical record

---

## Troubleshooting

### Issue: No Assets Found

**Symptoms:**
```
Step 2/8: Retrieving Tagged Assets from Source...
❌ No assets found with specified tags
```

**Causes:**
- Tags don't exist in source
- Tags not applied to assets
- Project name incorrect
- Case-sensitive mismatch

**Solution:**
1. Run Pre-Migration Check first
2. Verify tags in IICS
3. Check project name matches exactly
4. Apply tags to assets if missing

---

### Issue: Git Cherry-pick Failed

**Symptoms:**
```
Step 5/8: Cherry-picking Assets via Git...
❌ Git operation failed: CONFLICT
```

**Causes:**
- Conflicting changes in branches
- Asset modified in both branches
- Git repository out of sync

**Solution:**
1. Manually resolve conflicts in Git
2. Sync branches before migration
3. Use fresh clone
4. Contact Git administrator

---

### Issue: Pull Operation Timeout

**Symptoms:**
```
Step 6/8: Pulling Assets to Target Environment...
❌ Pull operation timed out after 30 minutes
```

**Causes:**
- Large number of assets
- Network issues
- Target IICS overloaded
- Invalid commit hash

**Solution:**
1. Increase timeout in config.py
2. Retry migration
3. Split into smaller batches
4. Check target IICS status

---

### Issue: Tagging Failed

**Symptoms:**
```
Step 7/8: Applying Post-Migration Tags...
⚠️  Failed to tag 5 assets
```

**Causes:**
- Assets not found in target
- Permission issues
- Asset paths changed

**Solution:**
1. Check pull operation succeeded
2. Verify asset existence in target
3. Check user permissions
4. Manually tag failed assets

---

### Issue: Database Recording Failed

**Symptoms:**
```
Step 8/8: Recording Migration in Database...
⚠️  Database recording skipped (migration still successful)
```

**Causes:**
- Database connection issues
- pymssql not installed
- Invalid database credentials

**Solution:**
1. Migration succeeded - database is optional
2. Install pymssql if needed
3. Check database connectivity
4. Verify credentials

---

## Advanced Features

### Batch Processing

Migrate multiple projects:
```json
{
  "ProjectName": ["Project1", "Project2", "Project3"]
}
```

**Note:** Only first project processed currently. For multiple projects, run separate migrations.

### Custom Asset Types

Add new asset types in `config.py`:
```python
TYPE_EXTENSIONS = {
    "CUSTOM_TYPE": [["custom.xml"], ["custom.xml", "zip"]]
}
```

### Publish Option

```json
{
  "Publish": 1  // 0=Save only, 1=Save and Publish
}
```

**Note:** Publishing validates assets immediately but takes longer.

---

## Git Repository Structure

Expected structure:
```
repo/
└── Explore/
    └── ProjectName/
        ├── Default/
        │   ├── Mapping1.dtemplate.xml
        │   ├── Mapping1.dtemplate.xml.zip
        │   └── Taskflow1.taskflow.xml
        └── Connections/
            └── Salesforce.AI_CONNECTION.xml
```

---

## API Endpoints Used

```
# Authentication
POST /saas/public/core/v3/login

# Asset Retrieval
GET /public/core/v3/tagging/{tag}/objects

# Project/Folder Management
POST /public/core/v3/projects
GET  /public/core/v3/projects
POST /public/core/v3/folders

# Asset Pull
POST /public/core/v3/commit/pull
GET  /public/core/v3/commit/pull/{taskId}

# Asset Lookup
POST /public/core/v3/lookup

# Tagging
POST /public/core/v3/tagging
```

---

## Security Considerations

⚠️ **Important:**

1. **Credentials** - Never commit config files with passwords
2. **Git Tokens** - Use personal access tokens with minimal permissions
3. **Rotate Secrets** - Regularly rotate passwords and tokens
4. **Audit Logs** - Review logs before sharing
5. **Database** - Secure database connection strings
6. **Git Cleanup** - Temporary repos are cleaned up automatically

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-06-28 | Initial release with 8-step workflow |
| 1.1 | 2026-06-28 | Added standardized logging format |
| 1.2 | 2026-06-28 | Integrated with Slack bot automation |
| 1.3 | 2026-06-28 | Removed custom exception classes, uses standard Python exceptions |

---

## Support

For issues or questions:
1. Check logs in `Logs/CICDMigration.log`
2. Review error messages and stack traces
3. Verify configuration fields
4. Check network connectivity to IICS and Git
5. Contact IICS administrator for environment issues
6. Review Git repository for conflicts

---

## Quick Reference

### Minimal Config

```json
{
  "ProjectName": ["MyProject"],
  "IICS_SRC_username": "source@example.com",
  "IICS_SRC_password": "src_pass",
  "IICS_SRC_region": "dm-us",
  "IICS_TGT_username": "target@example.com",
  "IICS_TGT_password": "tgt_pass",
  "IICS_TGT_region": "dm-us",
  "PreMigration_Tag": ["ReadyToMigrate"],
  "PostMigration_Tag": ["Migrated"],
  "Git_Repository_URL": "https://github.com/org/repo.git",
  "Git_config_useremail": "user@example.com",
  "Git_config_username": "User Name",
  "Git_password": "ghp_token",
  "Git_SRC_Branch": "DEV",
  "Git_TGT_Branch": "QA",
  "Publish": 0,
  "logFileDir": "Logs"
}
```

### Success Criteria

✅ All 8 steps complete without errors  
✅ Commit hash returned  
✅ Asset count matches expected  
✅ Post-migration tags applied  
✅ Logs show no critical errors  

---

**This tool automates your entire IICS migration workflow!** 🚀
