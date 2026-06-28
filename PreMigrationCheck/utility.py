"""
Utility Functions for File Operations
"""
import os
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List


def write_excel_report(logger: logging.Logger, file_dir: str, file_name: str,
                       sheet_objects: Dict[str, List[Dict]]) -> str:
    """
    Write data to Excel file with multiple sheets

    Args:
        logger: Logger instance
        file_dir: Directory to save file (e.g., 'Reports')
        file_name: Filename with timestamp (e.g., 'PreMigrationReport_20260628_143045.xlsx')
        sheet_objects: Dictionary mapping sheet names to data lists

    Returns:
        Full path to created file

    Raises:
        Exception: If file creation fails
    """
    try:
        os.makedirs(file_dir, exist_ok=True)

        # Use the filename as provided (timestamp already included from caller)
        file_path = os.path.join(file_dir, file_name)

        logger.info(f"Creating Excel report: {file_path}")

        # Check if we have any data
        has_data = any(data_list for data_list in sheet_objects.values())
        if not has_data:
            logger.error("No data to write to Excel file")
            raise ValueError("No data available to generate report")

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            sheets_written = 0
            for sheet_name, data_list in sheet_objects.items():
                try:
                    if not data_list:
                        logger.warning(f"No data for sheet '{sheet_name}', creating empty sheet with headers")
                        # Create empty sheet with headers based on sheet name
                        if sheet_name == 'CheckedOutAssets':
                            df = pd.DataFrame(columns=["Project", "Folder", "Asset"])
                        elif sheet_name == 'InvalidAssets':
                            df = pd.DataFrame(columns=["Project Name", "Asset", "Asset Type"])
                        elif sheet_name == 'Connections':
                            df = pd.DataFrame(columns=["Connection Name", "Connection Status"])
                        elif sheet_name == 'MigrationStat':
                            df = pd.DataFrame(columns=["Project", "Folder", "Asset", "AssetType", "Tags"])
                        else:
                            df = pd.DataFrame(columns=["Data"])

                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        sheets_written += 1
                        continue

                    df = pd.DataFrame(data_list)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.info(f"Sheet '{sheet_name}' written with {len(df)} rows")
                    sheets_written += 1

                except Exception as e:
                    logger.error(f"Failed to write sheet '{sheet_name}': {str(e)}")
                    continue

            if sheets_written == 0:
                raise ValueError("Failed to write any sheets to Excel file")

        logger.info(f"Excel report created successfully: {file_path}")
        return file_path

    except PermissionError as e:
        logger.error(f"Permission denied writing file: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to create Excel report: {str(e)}")
        raise
