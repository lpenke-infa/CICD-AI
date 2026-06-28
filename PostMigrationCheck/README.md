# Post-Migration Check Tool

## Overview

The Post-Migration Check Tool validates migrated IICS assets in the target environment after migration is complete. It verifies that assets were successfully migrated, generates comprehensive statistics, and creates a detailed Excel report for validation.

## Module Location

```
PostMigrationCheck/
```

## Entry Point

```
tools/post_migration_tool.py → PostMigrationCheck/main.py
```

---

## File Structure

### 1. `__init__.py`
- **Total Lines:** 6
- **Purpose:** Package initialization
- **Functions:** None (just imports)

---

### 2. `login.py`
- **Total Lines:** 110
- **Purpose:** IICS authentication with retry logic

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `retry_with_backoff()` | 10 | ~30 | Retry decorator with exponential backoff (3 retries) |
| `login()` | 40 | ~56 | Authenticates to IICS and returns session data |
| `iics_login()` | 96 | ~14 | Alias for backward compatibility |

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

### 3. `main.py` ⭐ (Core Orchestrator)
- **Total Lines:** 202
- **Purpose:** Main orchestration of post-migration validation workflow

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `create_logger()` | 24 | ~44 | Creates and configures logger instance |
| `run_post_migration_check()` | 68 | ~108 | **Main workflow** - Runs 3-step validation |
| `main()` | 176 | ~26 | Command-line entry point |

---

### 4. `migration_statistics.py`
- **Total Lines:** 88
- **Purpose:** Generates migration statistics report

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `generate_migration_statistics()` | 8 | ~80 | Creates statistics for Excel report (Project, Folder, Asset, Type, Tags) |

**Output Format:**
```python
[
    {
        'Project': 'MyProject',
        'Folder': 'MyFolder',
        'Asset': 'MyMapping',
        'AssetType': 'DTEMPLATE',
        'Tags': 'Tag1, Tag2'
    }
]
```

---

### 5. `tag_handling.py`
- **Total Lines:** 120
- **Purpose:** Retrieves assets by IICS tags

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `get_tagged_objects()` | 11 | ~76 | Gets objects with a specific tag from IICS API |
| `get_assets_by_tags()` | 87 | ~33 | Gets assets matching ANY of the provided tags (OR logic) |

**API Endpoints Used:**
```
GET /public/core/v3/tagging/{tag}/objects
```

---

### 6. `utility.py`
- **Total Lines:** 76
- **Purpose:** File operations (Excel report generation)

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `write_excel_report()` | 11 | ~65 | Writes multi-sheet Excel report with pandas/openpyxl |

**Excel Sheets Created:**
1. **MigrationStat** - Detailed migration statistics

---

## 3-Step Validation Workflow

### Step 1: Login to Target IICS
- Authenticates to target environment
- Gets session ID and API URL
- Uses retry logic with exponential backoff
- Validates credentials and connectivity

### Step 2: Retrieve Migrated Assets by Tags
- Gets all assets with specified post-migration tags
- These are tags applied during the CICD migration process
- Returns list of successfully migrated assets
- Uses OR logic for multiple tags

### Step 3: Generate Validation Report
- Creates comprehensive migration statistics
- Organizes by project/folder/asset type
- Includes all tag information
- Generates timestamped Excel report

---

## Configuration

### Required Fields

```json
{
  "IICS_TGT_username": "target_user@example.com",
  "IICS_TGT_password": "target_password",
  "IICS_TGT_region": "dm-us",
  
  "PostMigration_Tag": ["Migrated", "PostMigration"],
  "ProjectName": "MyProject",
  
  "logFileDir": "Logs",
  "reportFileDir": "Reports"
}
```

**Note:** Only target environment credentials needed (not source)

### Configuration Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `IICS_TGT_username` | String | Target IICS username | `"user@example.com"` |
| `IICS_TGT_password` | String | Target IICS password | `"password123"` |
| `IICS_TGT_region` | String | Target region code | `"dm-us"`, `"dm-eu"` |
| `PostMigration_Tag` | Array | Tags to validate (applied by CICD tool) | `["Migrated"]` |
| `ProjectName` | String/Array | IICS project name | `"MyProject"` or `["MyProject"]` |
| `logFileDir` | String | Log directory | `"Logs"` |
| `reportFileDir` | String | Report directory | `"Reports"` |

---

## Output

### Log File

**Location:**
```
Logs/PostMigrationCheck.log
```

**Format:**
```
2026-06-28 10:39:06,503 - PostMigrationCheck - INFO - [function:line] - Message
```

**Contents:**
- Session start/end timestamps
- Authentication details
- Asset retrieval progress
- Statistics generation
- Report file path
- Errors and warnings

---

### Report File

**Location:**
```
Reports/PostMigrationReport_YYYYMMDD_HHMMSS.xlsx
```

**Example:**
```
Reports/PostMigrationReport_20260628_143545.xlsx
```

**Excel Sheets:**

#### Sheet: MigrationStat

| Column | Description | Example |
|--------|-------------|---------|
| Project | Project name | MyProject |
| Folder | Folder path | Default/Mappings |
| Asset | Asset name | Customer_Mapping |
| AssetType | Type code | DTEMPLATE, MTT, TASKFLOW |
| Tags | Comma-separated tags | Migrated, PostMigration, v1.0 |

**Asset Types:**
- `DTEMPLATE` - Mapping
- `MTT` - Mapping Task
- `TASKFLOW` - Taskflow
- `DSS` - Synchronization Task
- `AI_CONNECTION` - Application Connection
- And 20+ more types

---

### Return Object

```python
{
    "success": True,
    "message": "Validation completed successfully",
    "asset_count": 25,
    "report_path": "Reports/PostMigrationReport_20260628_143545.xlsx"
}
```

**Failure Response:**
```python
{
    "success": False,
    "message": "No assets found with specified tags",
    "asset_count": 0,
    "report_path": None
}
```

---

## Usage

### Via Slack Bot (Recommended)

**After CICD Migration:**
```
Bot: 🎉 MIGRATION COMPLETED SUCCESSFULLY!

Would you like to run Post-Migration Validation to verify the migrated assets?
Reply with "yes" to proceed.

User: yes

Bot: 🔍 Starting Post-Migration Validation...
     🔐 Step 1/3: Authenticating to Target IICS...
     ✅ Logged into Target Org: MyTargetOrg
     📋 Step 2/3: Retrieving Migrated Assets...
     ✅ Found 25 migrated assets
     📊 Step 3/3: Generating Validation Report...
     
     ✅ POST-MIGRATION VALIDATION COMPLETED!
     📊 Summary:
        • Assets Validated: 25
        • Project: MyProject
        • Tags Checked: Migrated
     📄 Report Generated: Reports/PostMigrationReport_20260628_143545.xlsx
```

**Standalone Validation:**
```
User: Run post-migration validation with config post_migration_config.json
```

### Via Python

```python
from PostMigrationCheck.main import run_post_migration_check

result = run_post_migration_check('path/to/config.json')

if result['success']:
    print(f"✅ {result['asset_count']} assets validated")
    print(f"📄 Report: {result['report_path']}")
else:
    print(f"❌ Validation failed: {result['message']}")
```

### Via Command Line

```bash
python PostMigrationCheck/main.py path/to/config.json
```

---

## Integration with CICD Migration

### Automatic Flow

```
CICD Migration Completes
    ↓
Bot Prompts: "Run Post-Migration Validation?"
    ↓
User: "yes"
    ↓
Post-Migration Check Executes Automatically
    ↓
Report Uploaded to Slack
```

### Manual Flow

Can be run independently any time after migration:
1. Assets must have post-migration tags
2. Config must specify correct target environment
3. Tags must match those applied during migration

---

## What It Validates

### ✅ Asset Presence
- Confirms assets exist in target environment
- Verifies correct project and folder location
- Checks asset type accuracy

### ✅ Tag Verification
- Validates post-migration tags are applied
- Confirms tag values match expected
- Lists all tags on each asset

### ✅ Migration Completeness
- Counts total migrated assets
- Compares against expected count
- Identifies any missing assets

### ⚠️ What It Does NOT Check
- Asset functionality (use IICS testing)
- Connection validity (covered in Pre-Migration)
- Data quality
- Schedule execution

---

## Error Handling

### Retry Logic

All API calls use exponential backoff with 3 retries:
- Retry 1: Wait 1 second
- Retry 2: Wait 2 seconds
- Retry 3: Wait 4 seconds

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| No assets found | No assets with post-migration tags | Verify migration completed and tags applied |
| Authentication failed | Invalid target credentials | Check username/password/region |
| Connection timeout | Network issues | Check network connectivity to target |
| Invalid project | Project doesn't exist in target | Verify project was created during migration |
| Empty report | Project name mismatch | Ensure ProjectName matches asset paths |

---

## Dependencies

```python
import json
import sys
import os
import logging
from datetime import datetime
import pandas as pd
import requests
```

**Required Packages:**
- `pandas` - Excel report generation
- `openpyxl` - Excel file handling
- `requests` - IICS API calls

---

## Statistics

| Metric | Count |
|--------|-------|
| **Total Files** | 6 |
| **Total Lines** | ~602 |
| **Total Functions** | 7 |
| **Validation Steps** | 3 |
| **Excel Sheets** | 1 |
| **API Calls** | ~2-5 per run |
| **Avg Execution Time** | 1-3 minutes |

---

## Best Practices

1. **Run immediately after migration** - Validates migration success
2. **Review asset counts** - Compare with pre-migration counts
3. **Verify project/folder structure** - Ensure correct organization
4. **Check all tags** - Confirm expected tags are present
5. **Keep reports** - Historical record of migrations
6. **Compare reports** - Pre vs Post for completeness

---

## Troubleshooting

### Issue: No Assets Found

**Cause:** Post-migration tags not applied or wrong tag specified

**Solution:**
1. Verify CICD migration completed successfully
2. Check `PostMigration_Tag` in CICD config matches this config
3. Manually check assets in IICS for tags
4. Verify correct target environment

### Issue: Fewer Assets Than Expected

**Cause:** Some assets failed to migrate or tag application failed

**Solution:**
1. Compare with Pre-Migration report
2. Check CICD migration logs for errors
3. Verify all assets have post-migration tags
4. Re-run migration for missing assets

### Issue: Empty MigrationStat Sheet

**Cause:** ProjectName doesn't match asset paths

**Solution:**
1. Check exact project name in IICS
2. Verify case-sensitive match
3. Review sample asset paths in logs
4. Update ProjectName in config

### Issue: Report Not Generated

**Cause:** No write permissions or disk full

**Solution:**
1. Check `reportFileDir` exists
2. Verify write permissions
3. Ensure sufficient disk space

---

## Comparison: Pre vs Post

| Aspect | Pre-Migration Check | Post-Migration Check |
|--------|---------------------|----------------------|
| **When** | Before migration | After migration |
| **Environment** | Source + Target | Target only |
| **Purpose** | Identify issues | Verify success |
| **Steps** | 6 steps | 3 steps |
| **Checks** | Locked assets, invalid assets, connections | Asset presence, tags, counts |
| **Excel Sheets** | 4 sheets | 1 sheet |
| **Execution Time** | 2-5 minutes | 1-3 minutes |
| **Can Run Standalone** | Yes | Yes |

---

## Complete Migration Workflow

```
1. Pre-Migration Check
   ↓
   Review & Fix Issues
   ↓
2. CICD Migration
   ↓
   Migration Completes
   ↓
3. Post-Migration Check ← YOU ARE HERE
   ↓
   Validation Report
   ↓
4. User Acceptance Testing
```

---

## Report Analysis

### Healthy Migration Indicators

✅ Asset count matches expected  
✅ All assets have correct project/folder  
✅ Post-migration tags applied to all  
✅ Asset types are correct  
✅ No missing folders or projects  

### Red Flags

⚠️ Asset count lower than pre-migration  
⚠️ Assets in wrong projects/folders  
⚠️ Missing post-migration tags  
⚠️ Empty report or missing statistics  
⚠️ Asset type mismatches  

---

## Advanced Usage

### Multiple Tag Validation

Validate assets with multiple tags:
```json
{
  "PostMigration_Tag": ["Migrated", "Validated", "Release_v1.0"]
}
```

Uses OR logic - assets with ANY of these tags will be included.

### Project Array Support

Supports both string and array format:
```json
"ProjectName": "MyProject"
```
or
```json
"ProjectName": ["MyProject"]
```

Both formats work identically.

### Custom Report Location

Override default report directory:
```json
{
  "reportFileDir": "ValidationReports/Sprint_10"
}
```

---

## Integration Points

### With Slack Bot

Automatic integration:
- Bot prompts for validation after migration
- Real-time progress updates in Slack
- Report automatically uploaded to channel
- User can download with original filename

### With CICD Tool

Seamless handoff:
- CICD stores migration metadata
- Post-check uses same target credentials
- Validates tags applied by CICD
- Can run automatically or on-demand

### With Monitoring Systems

Export data for monitoring:
- Parse Excel report programmatically
- Track migration success rates
- Monitor asset counts over time
- Alert on validation failures

---

## API Endpoints Used

```
POST /saas/public/core/v3/login
  - Authenticate to target IICS

GET /public/core/v3/tagging/{tag}/objects
  - Get objects with specific tag
  - Called for each PostMigration_Tag
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-06-28 | Initial release with 3-step validation |
| 1.1 | 2026-06-28 | Added timestamped reports and reportFileDir |
| 1.2 | 2026-06-28 | Integrated with CICD migration workflow |

---

## Support

For issues or questions:
1. Check logs in `Logs/PostMigrationCheck.log`
2. Review error messages in console output
3. Compare with pre-migration report
4. Contact IICS administrator for environment issues

---

## Quick Reference

### Minimal Config

```json
{
  "IICS_TGT_username": "user@example.com",
  "IICS_TGT_password": "password",
  "IICS_TGT_region": "dm-us",
  "PostMigration_Tag": ["Migrated"],
  "ProjectName": "MyProject",
  "logFileDir": "Logs",
  "reportFileDir": "Reports"
}
```

### Success Criteria

✅ `success: True` in return object  
✅ `asset_count > 0`  
✅ Report file generated  
✅ All expected assets present  

---

**This tool validates your migration was successful!** ✅
