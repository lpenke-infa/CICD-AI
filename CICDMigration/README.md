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
- **Total Lines:** 255
- **Purpose:** Git operations for asset migration

#### Functions

| Function | Line | Purpose |
|----------|------|---------|
| `run_git_command()` | 13 | Executes Git commands via subprocess (no `shell=True`) with timeout, error handling and logging |
| `git_config()` | 61 | Configures Git user, clones/fetches repo; returns auth URL, domain, repo dir |
| `git_operations()` | 122 | Checks out source & target branches, brings each asset file across, commits & pushes |
| `cherrypick()` | 218 | Main entry point; orchestrates `git_config` + `git_operations`, cleans up repo dir |

**Git Workflow (branch/file checkout — not `git cherry-pick`):**
1. Clone/fetch repository and configure Git user credentials
2. Checkout the target branch
3. For each asset, `git checkout <SRC_Branch> -- <asset file>` to bring the source version onto the target branch
4. `git add -A`, commit, and push to the remote target branch
5. Return the target commit hash

> **Note:** Despite the module name, no `git cherry-pick` command is used — assets
> are transferred by checking individual files out of the source branch onto the target branch.

---

### 3. `config.py`
- **Total Lines:** 39
- **Purpose:** Configuration constants and asset type mappings

#### Constants

```python
# API / operation configuration
API_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2
GIT_OPERATION_TIMEOUT = 300
PULL_STATUS_CHECK_INTERVAL = 15
ASSETS_PER_PAGE = 200
TAG_BATCH_SIZE = 100

# Asset type → Git file-format mapping (24 types)
# Each value is a list of [dot-prefix-flag, extension] entries.
DICT_FILE_FORMAT = {
    "DTEMPLATE": [[1, "json"], [0, "zip"]],
    "MTT": [...],
    "TASKFLOW": [...],
    # ... 21 more types
}
```

**Git-migratable asset types (24, keys of `DICT_FILE_FORMAT`):**
DTEMPLATE, MTT, TASKFLOW, AtScaleDTemplate, DTT, DBMI_TASK, DICTIONARY,
BSERVICE, CLEANSE, DMAPPLET, PARSE, RULE_SPECIFICATION, VERIFIER, LABELER,
AI_CONNECTION, PROCESS_OBJECT, GUIDE, AI_SERVICE_CONNECTOR, PROCESS,
MI_FILE_LISTENER, MI_TASK, STRUCTURE_DISCOVERY, UDF, FWCONFIG

---

### 4. `createProjectsAndFolders.py`
- **Total Lines:** 302
- **Purpose:** Creates required project and folder structure in target environment

#### Functions

| Function | Line | Purpose |
|----------|------|---------|
| `extract_folder_and_project()` | 11 | Extracts unique project→folder structure from asset metadata |
| `is_project_or_folder_exists()` | 47 | Checks via API if a project/folder location exists |
| `create_project()` | 81 | Creates a new project in target IICS |
| `get_project_id()` | 140 | Retrieves project ID by name |
| `create_folder()` | 184 | Creates a new folder under a project |
| `create_projects_and_folders()` | 241 | Main entry point - creates all required projects and folders |

**API Endpoints:** IICS `/frs/v1/Projects` (and folder) endpoints for lookup/create.

---

### 5. `database.py`
- **Total Lines:** 124
- **Purpose:** Records migration audit trail in a local SQLite database

#### Functions

| Function | Line | Purpose |
|----------|------|---------|
| `add_record()` | 38 | Inserts migration record into the SQLite database (optional; never raises) |

**Storage:** Uses Python's built-in `sqlite3` module — a single local file, no server
required (no SQL Server, no `pymssql`). The database file defaults to
`Database/deployments.db` in the project root and can be overridden with the
`DB_PATH` environment variable. The table is created automatically on first use.

**Database Schema:**
```sql
CREATE TABLE IF NOT EXISTS Deployment_Details (
    Id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ProjectName     TEXT    NOT NULL,
    IICSSourceOrg   TEXT,
    IICSSourceOrgID TEXT,
    CommitHash      TEXT,
    Tag             TEXT,
    Deployment_Date TEXT    NOT NULL,
    Rollback_Date   TEXT,
    IICSTargetOrgID TEXT,
    IICSTargetOrg   TEXT,
    AssetsMigrated  INTEGER
);
```

**Note:** Database logging is optional. `add_record()` never raises — on any failure
it logs the error and returns `False`, so a database problem cannot abort a successful
migration.

---

### 6. `credentials_db.py`
- **Total Lines:** 220
- **Purpose:** Stores IDMC connection credentials in a separate local SQLite database

#### Functions

| Function | Line | Purpose |
|----------|------|---------|
| `save_credentials()` | 48 | Inserts or updates the credentials row for an org (upsert keyed by OrgName) |
| `get_credentials()` | 106 | Fetches the stored credentials for an org (returns dict or None) |
| `list_credentials()` | 148 | Lists all stored credential rows (passwords omitted) |
| `delete_credentials()` | 188 | Deletes the credentials row for an org |

**Storage:** Uses Python's built-in `sqlite3` module in a database file separate from the
migration audit DB. Defaults to `Database/idmc_credentials.db` in the project root and can
be overridden with the `IDMC_CREDS_DB_PATH` environment variable. One row per org
(table `Idmc_Credentials`), with columns `OrgName` (primary key), `Entity`, `Username`,
`Password`, `Region`, `UpdatedAt`.

**Table Schema:**
```sql
CREATE TABLE IF NOT EXISTS Idmc_Credentials (
    OrgName    TEXT    PRIMARY KEY,
    Entity     TEXT,
    Username   TEXT    NOT NULL,
    Password   TEXT    NOT NULL,
    Region     TEXT,
    UpdatedAt  TEXT
);
```

> **Security:** Passwords are stored in plain text, so the database file must be kept
> local and excluded from version control (git-ignored).

---

### 7. `logger.py`
- **Total Lines:** 59
- **Purpose:** Logging configuration for CICD operations

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `create_logger()` | 9 | ~50 | Creates and configures logger with file and console handlers |

**Log Format:**
```
2026-06-28 10:39:06 - CICDMigration - INFO - [function:line] - Message
```

**Log File:**
```
Logs/CICDMigration.log  (append mode)
```

---

### 8. `login.py`
- **Total Lines:** 63
- **Purpose:** IICS authentication

#### Functions

| Function | Line | Purpose |
|----------|------|---------|
| `login()` | 11 | Authenticates to IICS and returns session data |

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

### 9. `main.py` ⭐ (Core Orchestrator)
- **Total Lines:** 211
- **Purpose:** Main orchestration of 8-step migration workflow

#### Functions

| Function | Line | Purpose |
|----------|------|---------|
| `load_configuration()` | 22 | Loads and parses configuration JSON file |
| `run_migration()` | 47 | **Main workflow** - Orchestrates all 8 migration steps |
| `main()` | 191 | Command-line entry point |

Config is validated up front via `common.config_validation.validate_config(..., config_type='cicd')` (through `utils.validate_input_data`).

---

### 10. `postMigrationTag.py`
- **Total Lines:** 206
- **Purpose:** Applies tags to migrated assets in target environment

#### Functions

| Function | Line | Purpose |
|----------|------|---------|
| `lookup_v3()` | 11 | Looks up asset IDs in target environment by path; builds tag request bodies |
| `post_migration_tagging_v3()` | 83 | Applies tags to assets in batches (with optional progress callback) |
| `post_migration_tag()` | 161 | Main entry point for post-migration tagging |

**Tagging Strategy:**
- Batch processing (`TAG_BATCH_SIZE` = 100 assets per batch)
- Retry logic for failed tags
- Validates asset existence before tagging

**API Endpoints:**
```
POST /public/core/v3/lookup     - Lookup asset IDs
POST /public/core/v3/TagObjects - Apply tags
```

---

### 11. `pull.py`
- **Total Lines:** 218
- **Purpose:** Imports assets from Git to target IICS environment

#### Functions

| Function | Line | Purpose |
|----------|------|---------|
| `pull_v3()` | 12 | Initiates a pull from a Git commit; returns response with pullActionId |
| `get_pull_status_v3()` | 89 | Polls pull status until SUCCESSFUL/FAILED/CANCELLED (max 120 checks) |
| `pull_assets()` | 174 | Main entry point; orchestrates `pull_v3` + status monitoring |

**Pull Workflow:**
1. Initiate pull from a specific Git commit
2. Poll status every `PULL_STATUS_CHECK_INTERVAL` (15) seconds
3. Wait for completion (can take several minutes)
4. Validate success

**API Endpoints:** IICS `/public/core/v3/pull` (initiate) and pull-status endpoints.

---

### 12. `taggedAssets.py`
- **Total Lines:** 223
- **Purpose:** Retrieves tagged assets from source environment

#### Functions

| Function | Line | Purpose |
|----------|------|---------|
| `generate_git_path()` | 11 | Generates Git file paths for an asset from its path/formats/type |
| `retrieve_tagged_assets()` | 45 | Retrieves assets with a tag from IICS (paginated) |
| `filter_and_parse_path()` | 95 | Filters assets by project and builds git_paths + metadata |
| `tagged_assets()` | 157 | Main entry point - gets tagged assets across all tags, deduped |

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

### 13. `utils.py`
- **Total Lines:** 106
- **Purpose:** Utility functions for retry logic and validation

#### Functions

| Function | Line | Purpose |
|----------|------|---------|
| `retry_with_backoff()` | 10 | Retries a callable with exponential backoff on `RequestException` |
| `sanitize_for_log()` | 46 | Redacts credentials embedded in URLs before logging |
| `validate_input_data()` | 72 | Delegates to `common.config_validation.validate_config(config_type='cicd')` |

**Retry Configuration:**
- Max retries: 3
- Backoff factor: 2, with full jitter — each wait is `random.uniform(0, 2 ** attempt)` seconds (randomized, not fixed)
- Applies only to HTTP/API calls (wraps `requests` calls); retries on `requests.exceptions.RequestException`. Git commands are not retried.

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

### Step 5: Transfer Assets via Git (per-file checkout) 🌿
- Clones/fetches Git repository
- Configures Git credentials (`user.name` / `user.email`)
- Checks out and pulls the source branch (e.g., DEV)
- Checks out and pulls the target branch (e.g., QA)
- For each asset, `git checkout <source-branch> -- <asset file>` brings the source version onto the target branch
- `git add -A`, commits, and pushes to the remote target branch
- Returns the target commit hash

> **Note:** Despite the module name (`cherrypick.py`), no `git cherry-pick` command is
> used — assets are transferred by checking individual files out of the source branch
> onto the target branch.

**Input:** Git config, asset Git paths  
**Output:** Commit hash for pull operation

**Git Commands:**
```bash
git config --global user.name / user.email
git clone <repo>                              # or: git -C <repo> fetch --all if it exists
git checkout <source-branch>
git pull <repo> <source-branch>
git checkout <target-branch>
git pull <repo> <target-branch>
git checkout <source-branch> -- <asset file>  # once per asset
git add -A
git commit -m "Migration: <tag>"
git push <repo> <target-branch>
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
- Inserts migration record into the local SQLite audit database (`Database/deployments.db`)
- Records source/target org details
- Stores commit hash for rollback
- Logs asset count and timestamp

**Input:** Migration metadata  
**Output:** Database record (optional)

**Note:** Database step is optional and will continue on failure. `add_record()` never raises;
it logs and returns `False` so a DB problem cannot abort a successful migration.

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
2026-06-28 10:39:06 - CICDMigration - INFO - [function:line] - Message
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
from CICDMigration.main import run_migration

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

HTTP/API calls use exponential backoff with full jitter and up to 3 attempts. On each
failure the wait is a random value in `[0, backoff_factor ** attempt)` seconds
(`random.uniform(0, backoff_factor ** attempt)`), so the delays are randomized rather
than fixed:
- Retry after attempt 1: random wait in [0, 1) second
- Retry after attempt 2: random wait in [0, 2) seconds
- Retry after attempt 3 exhausts the retries (the exception is raised)

The jitter avoids a thundering herd when multiple requests retry in lockstep.

Applies to:
- IICS API calls only (login, asset retrieval, project/folder creation, pull initiation, lookup, tagging)

**Not** retried:
- Git operations (`run_git_command`, `git_config`, `git_operations` in `cherrypick.py`) —
  these run without the retry decorator and fail immediately on error

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| No assets found | No assets with pre-migration tags | Run pre-migration check first |
| Authentication failed | Invalid credentials | Verify username/password/region |
| Git clone failed | Invalid repo URL or token | Check Git_Repository_URL and Git_password |
| Git checkout failed | Branch missing, or no assets could be checked out from the source branch | Verify source/target branches exist and the asset files are present on the source branch |
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
import time
from typing import Dict, List, Tuple
from datetime import datetime
import sqlite3  # Built-in; used for database logging
import requests
```

**Required Packages:**
- `requests` - IICS API calls
- `sqlite3` - Database logging (Python standard library, no install needed)
- `git` - Git command-line tool must be installed

**System Requirements:**
- Git installed and accessible in PATH
- Network access to IICS and Git repository
- Write permissions for local Git operations

---

## Statistics

| Metric | Count |
|--------|-------|
| **Total Files** | 13 |
| **Total Lines** | ~2,050 |
| **Total Functions** | 34 (top-level) |
| **Total Classes** | 0 (uses standard exceptions) |
| **Migration Steps** | 8 |
| **API Endpoints** | ~10 |
| **Git-migratable Asset Types** | 24 |
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

### Issue: Git Asset Checkout Failed

**Symptoms:**
```
Step 5/8: Transferring Assets via Git...
❌ Git operation failed / No assets were successfully checked out
```

**Causes:**
- Source or target branch does not exist
- Asset files are not present on the source branch
- Git repository out of sync
- Invalid credentials for push

**Solution:**
1. Verify source and target branches exist in the repository
2. Confirm the tagged asset files are committed on the source branch
3. Sync/fetch branches before migration
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
- Unable to create/write the SQLite file
- No write permission for the `Database/` directory
- Invalid `DB_PATH` override

**Solution:**
1. Migration succeeded - database is optional
2. Ensure the `Database/` directory is writable (it is created automatically)
3. Check any `DB_PATH` environment override points to a valid path
4. Review the logged DB error for details

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

Add new asset types to the `DICT_FILE_FORMAT` mapping in `config.py`:
```python
DICT_FILE_FORMAT = {
    "CUSTOM_TYPE": [[1, "json"], [0, "zip"]]
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
# Authentication (login.py)
POST https://{region}.informaticacloud.com/saas/public/core/v3/login

# Asset Retrieval by tag (taggedAssets.py)
GET  /public/core/v3/objects?q=tag=='{tag}'&skip={skip}

# Project/Folder Management (createProjectsAndFolders.py)
GET  /public/core/v3/objects?q=location=='{path}'   # existence check
POST /frs/v1/Projects                               # create project
GET  /frs/v1/Projects?$filter=(name eq '{name}')    # get project id
POST /frs/v1/Projects('{projectId}')/Folders        # create folder

# Asset Pull (pull.py)
POST /public/core/v3/pull                            # initiate pull
GET  /public/core/v3/pull/{pullActionId}?expand=objects   # poll status

# Asset Lookup (postMigrationTag.py)
POST /public/core/v3/lookup

# Tagging (postMigrationTag.py)
POST /public/core/v3/TagObjects
```

---

## Security Considerations

⚠️ **Important:**

1. **Credentials** - Never commit config files with passwords
2. **Git Tokens** - Use personal access tokens with minimal permissions
3. **Rotate Secrets** - Regularly rotate passwords and tokens
4. **Audit Logs** - Review logs before sharing
5. **Database** - The SQLite files live under `Database/`. The credentials DB
   (`idmc_credentials.db`) stores passwords in plain text, so keep it local and git-ignored
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
