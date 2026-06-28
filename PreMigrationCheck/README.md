# Pre-Migration Check Tool

## Overview

The Pre-Migration Check Tool validates source IICS assets before migration to identify potential issues and ensure migration readiness. It performs comprehensive validation across 6 steps and generates a detailed Excel report.

## Module Location

```
PreMigrationCheck/
```

## Entry Point

```
tools/pre_migration_tool.py → PreMigrationCheck/main.py
```

---

## File Structure

### 1. `__init__.py`
- **Total Lines:** 6
- **Purpose:** Package initialization
- **Functions:** None (just imports)

---

### 2. `asset_validation.py`
- **Total Lines:** 147
- **Purpose:** Validates assets for migration readiness

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `get_checked_out_assets()` | 11 | ~80 | Gets list of assets that are checked out (locked) and cannot be migrated |
| `validate_assets()` | 92 | ~55 | Validates assets to find invalid/corrupted assets |

**What it checks:**
- ✅ Checked-out assets (locked by users)
- ✅ Invalid assets (corrupted or incomplete)

---

### 3. `connection_check.py`
- **Total Lines:** 151
- **Purpose:** Validates connections availability in target environment

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `get_connection_dependencies()` | 10 | ~73 | Extracts all connection dependencies from source assets |
| `check_connection_status_in_target()` | 83 | ~68 | Checks if required connections exist in target environment |

**What it checks:**
- ✅ Connection dependencies in source assets
- ✅ Connection availability in target environment
- ✅ Connection status (active/inactive)

---

### 4. `login.py`
- **Total Lines:** 93
- **Purpose:** IICS authentication with retry logic

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `retry_with_backoff()` | 10 | ~30 | Retry decorator with exponential backoff (3 retries) |
| `login()` | 40 | ~53 | Authenticates to IICS and returns session data |

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

### 5. `main.py` ⭐ (Core Orchestrator)
- **Total Lines:** 336
- **Purpose:** Main orchestration of pre-migration check workflow

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `create_logger()` | 28 | ~44 | Creates and configures logger instance |
| `run_pre_migration_check()` | 72 | ~236 | **Main workflow** - Runs all 6 validation steps |
| `main()` | 308 | ~28 | Command-line entry point |

---

### 6. `migration_statistics.py`
- **Total Lines:** 81
- **Purpose:** Generates migration statistics report

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `generate_migration_statistics()` | 8 | ~73 | Creates statistics for Excel report (Project, Folder, Asset, Type, Tags) |

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

### 7. `tag_handling.py`
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

### 8. `utility.py`
- **Total Lines:** 84
- **Purpose:** File operations (Excel report generation)

#### Functions

| Function | Line | Lines | Purpose |
|----------|------|-------|---------|
| `write_excel_report()` | 11 | ~73 | Writes multi-sheet Excel report with pandas/openpyxl |

**Excel Sheets Created:**
1. **CheckedOutAssets** - Locked assets
2. **InvalidAssets** - Corrupted assets
3. **Connections** - Connection availability
4. **MigrationStat** - Migration statistics

---

## 6-Step Validation Workflow

### Step 1: Login to Source IICS
- Authenticates to source environment
- Gets session ID and API URL
- Uses retry logic with exponential backoff

### Step 2: Retrieve Assets by Tags
- Gets all assets with specified pre-migration tags
- Returns list of assets to migrate
- Uses OR logic for multiple tags

### Step 3: Check for Checked-Out Assets
- Identifies locked assets
- These cannot be migrated until checked in
- Returns list of checked-out assets with Project/Folder/Asset details

### Step 4: Validate Assets
- Checks for invalid/corrupted assets
- Identifies assets that may fail migration
- Returns list with Project/Asset/Type details

### Step 5: Generate Statistics
- Creates migration statistics
- Organizes by project/folder/asset type
- Includes tag information

### Step 6: Check Connections in Target
- Logs into target environment
- Extracts connection dependencies from source assets
- Validates required connections exist in target
- Returns connection status (Available/Not Available)

---

## Configuration

### Required Fields

```json
{
  "IICS_SRC_username": "source_user@example.com",
  "IICS_SRC_password": "source_password",
  "IICS_SRC_region": "dm-us",
  
  "IICS_TGT_username": "target_user@example.com",
  "IICS_TGT_password": "target_password",
  "IICS_TGT_region": "dm-us",
  
  "PreMigration_Tag": ["PreMigration", "ReadyToMigrate"],
  "ProjectName": "MyProject",
  
  "logFileDir": "Logs",
  "reportFileDir": "Reports"
}
```

### Configuration Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `IICS_SRC_username` | String | Source IICS username | `"user@example.com"` |
| `IICS_SRC_password` | String | Source IICS password | `"password123"` |
| `IICS_SRC_region` | String | Source region code | `"dm-us"`, `"dm-eu"` |
| `IICS_TGT_username` | String | Target IICS username | `"user@example.com"` |
| `IICS_TGT_password` | String | Target IICS password | `"password123"` |
| `IICS_TGT_region` | String | Target region code | `"dm-us"`, `"dm-eu"` |
| `PreMigration_Tag` | Array | Tags to filter assets | `["Tag1", "Tag2"]` |
| `ProjectName` | String | IICS project name | `"MyProject"` |
| `logFileDir` | String | Log directory | `"Logs"` |
| `reportFileDir` | String | Report directory | `"Reports"` |

---

## Output

### Log File

**Location:**
```
Logs/PreMigrationCheck.log
```

**Format:**
```
2026-06-28 10:39:06,503 - PreMigrationCheck - INFO - [function:line] - Message
```

**Contents:**
- Session start/end timestamps
- Each validation step with details
- Asset counts and statistics
- Errors and warnings

---

### Report File

**Location:**
```
Reports/PreMigrationReport_YYYYMMDD_HHMMSS.xlsx
```

**Example:**
```
Reports/PreMigrationReport_20260628_143045.xlsx
```

**Excel Sheets:**

#### Sheet 1: CheckedOutAssets
| Column | Description |
|--------|-------------|
| Project | Project name |
| Folder | Folder path |
| Asset | Asset name |

#### Sheet 2: InvalidAssets
| Column | Description |
|--------|-------------|
| Project Name | Project name |
| Asset | Asset name |
| Asset Type | Type code (DTEMPLATE, MTT, etc.) |

#### Sheet 3: Connections
| Column | Description |
|--------|-------------|
| Connection Name | Connection name |
| Connection Status | Available / Not Available |

#### Sheet 4: MigrationStat
| Column | Description |
|--------|-------------|
| Project | Project name |
| Folder | Folder path |
| Asset | Asset name |
| AssetType | Type code |
| Tags | Comma-separated tags |

---

### Return Object

```python
{
    "success": True,
    "message": "Pre-migration check completed successfully",
    "asset_count": 25,
    "checked_out_count": 2,
    "invalid_count": 1,
    "connection_count": 10,
    "report_path": "Reports/PreMigrationReport_20260628_143045.xlsx"
}
```

---

## Usage

### Via Slack Bot

```
User: Run pre-migration check with config file pre_migration_config.json
```

### Via Python

```python
from PreMigrationCheck.main import run_pre_migration_check

result = run_pre_migration_check('path/to/config.json')

if result['success']:
    print(f"✅ {result['asset_count']} assets validated")
    print(f"⚠️  {result['checked_out_count']} checked-out assets")
    print(f"❌ {result['invalid_count']} invalid assets")
    print(f"🔌 {result['connection_count']} connections checked")
    print(f"📄 Report: {result['report_path']}")
```

### Via Command Line

```bash
python PreMigrationCheck/main.py path/to/config.json
```

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
| No assets found | No assets with specified tags | Verify tags exist in source |
| Authentication failed | Invalid credentials | Check username/password |
| Connection timeout | Network issues | Check network connectivity |
| Invalid project | Project doesn't exist | Verify project name |

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
| **Total Files** | 8 |
| **Total Lines** | ~1,018 |
| **Total Functions** | 11 |
| **Validation Steps** | 6 |
| **Excel Sheets** | 4 |
| **API Calls** | ~5-10 per run |
| **Avg Execution Time** | 2-5 minutes |

---

## Best Practices

1. **Always run before migration** - Identifies issues early
2. **Review checked-out assets** - Check in or skip them
3. **Fix invalid assets** - Repair or exclude from migration
4. **Verify connections** - Create missing connections in target
5. **Keep reports** - Historical record of validations

---

## Troubleshooting

### Issue: No Assets Found

**Cause:** Tags don't exist or aren't applied to assets

**Solution:**
1. Verify tags exist in IICS
2. Check tag names (case-sensitive)
3. Ensure assets are tagged in source

### Issue: Connection Check Fails

**Cause:** Target credentials invalid or network issues

**Solution:**
1. Verify target credentials
2. Check target region code
3. Test network connectivity

### Issue: Report Not Generated

**Cause:** No write permissions or disk full

**Solution:**
1. Check `reportFileDir` exists
2. Verify write permissions
3. Ensure sufficient disk space

---

## Integration

### With CICD Migration

```
Pre-Migration Check → Review Issues → CICD Migration → Post-Migration Check
```

### With Slack Bot

The tool integrates with the Slack bot for conversational interaction:
1. Upload config file or select existing
2. Bot runs validation with real-time updates
3. Excel report uploaded to Slack channel
4. Review and proceed to migration

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-06-28 | Initial release with 6-step validation |
| 1.1 | 2026-06-28 | Added timestamped reports and reportFileDir |

---

## Support

For issues or questions:
1. Check logs in `Logs/PreMigrationCheck.log`
2. Review error messages in Excel report
3. Contact IICS administrator for environment issues

---

**This tool ensures your migration is safe before starting!** ✅
