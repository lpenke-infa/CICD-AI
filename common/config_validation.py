"""
Configuration validation using modular functional approach
Simple validation functions without OOP
"""
import re
from typing import List, Dict, Any


# ============================================================================
# VALIDATION FUNCTIONS - Each validates one specific rule
# ============================================================================

def validate_required_field(config: dict, field_name: str) -> None:
    """Check if required field exists and is not empty"""
    if field_name not in config:
        raise ValueError(f"Required field missing: {field_name}")

    value = config[field_name]
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"Field cannot be empty: {field_name}")


def validate_string_field(config: dict, field_name: str, min_length: int = 1) -> None:
    """Validate field is a string with minimum length"""
    if field_name not in config:
        return

    value = config[field_name]
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string, got {type(value).__name__}")

    if len(value) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")


def validate_integer_field(config: dict, field_name: str, min_val: int = None, max_val: int = None) -> None:
    """Validate field is an integer within range"""
    if field_name not in config:
        return

    value = config[field_name]
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer, got {type(value).__name__}")

    if min_val is not None and value < min_val:
        raise ValueError(f"{field_name} must be >= {min_val}, got {value}")

    if max_val is not None and value > max_val:
        raise ValueError(f"{field_name} must be <= {max_val}, got {value}")


def validate_array_field(config: dict, field_name: str, min_length: int = None, max_length: int = None) -> None:
    """Validate field is an array with length constraints"""
    if field_name not in config:
        return

    value = config[field_name]
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be an array/list, got {type(value).__name__}")

    if min_length is not None and len(value) < min_length:
        raise ValueError(f"{field_name} must have at least {min_length} item(s), got {len(value)}")

    if max_length is not None and len(value) > max_length:
        raise ValueError(f"{field_name} must have at most {max_length} item(s), got {len(value)}")


def validate_project_name(config: dict) -> None:
    """Validate ProjectName: alphanumeric + spaces + underscore + hyphen"""
    field_name = 'ProjectName'
    if field_name not in config:
        return

    value = config[field_name]
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    if not re.match(r'^[A-Za-z0-9 _-]+$', value):
        raise ValueError(
            f'{field_name} must contain only alphanumeric characters, spaces, underscores, and hyphens. '
            f'Got: "{value}"'
        )


def validate_region(config: dict, field_name: str) -> None:
    """Validate IICS region format: dm-XX or dmN-XX, auto-lowercase"""
    if field_name not in config:
        return

    value = config[field_name]
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    # Auto-lowercase
    value_lower = value.lower()

    if not re.match(r'^dm[0-9]?-[a-z]{2,3}$', value_lower):
        raise ValueError(
            f'{field_name} must match pattern dm-XX or dmN-XX (e.g., dm-us, dm1-em). '
            f'Got: "{value}"'
        )

    # Update config with lowercased value
    config[field_name] = value_lower


def validate_tags(config: dict, field_name: str) -> None:
    """Validate tags: alphanumeric + underscore + hyphen + dot only"""
    if field_name not in config:
        return

    tags = config[field_name]
    if not isinstance(tags, list):
        raise ValueError(f"{field_name} must be an array/list")

    for tag in tags:
        if not isinstance(tag, str) or not tag:
            raise ValueError(f'{field_name} contains empty or non-string tag')

        if not re.match(r'^[A-Za-z0-9_.-]+$', tag):
            raise ValueError(
                f'{field_name} tag "{tag}" must contain only alphanumeric characters, '
                f'underscores, hyphens, and dots'
            )


def validate_email(config: dict, field_name: str) -> None:
    """Validate email format"""
    if field_name not in config:
        return

    value = config[field_name]
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    # Simple email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        raise ValueError(f'{field_name} must be a valid email address. Got: "{value}"')


def validate_https_url(config: dict, field_name: str) -> None:
    """Validate URL uses HTTPS protocol"""
    if field_name not in config:
        return

    value = config[field_name]
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    if not value.startswith('https://'):
        raise ValueError(f'{field_name} must start with https://. Got: "{value}"')

    # Basic URL validation
    if not re.match(r'^https://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', value):
        raise ValueError(f'{field_name} must be a valid HTTPS URL. Got: "{value}"')


def validate_git_branch(config: dict, field_name: str) -> None:
    """Validate git branch name: alphanumeric + / - _ . only"""
    if field_name not in config:
        return

    value = config[field_name]
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    if not re.match(r'^[A-Za-z0-9/_.-]+$', value):
        raise ValueError(
            f'{field_name} "{value}" contains invalid characters. '
            f'Only alphanumeric, /, -, _, . are allowed'
        )


def validate_source_not_equal_target(config: dict, src_field: str, tgt_field: str, error_msg: str) -> None:
    """Validate source and target fields are different"""
    if src_field not in config or tgt_field not in config:
        return

    if config[src_field] == config[tgt_field]:
        raise ValueError(error_msg)


def warn_and_override_directory(config: dict, field_name: str, default_value: str) -> List[str]:
    """Warn user if custom directory provided and override with default"""
    warnings = []

    if field_name in config and config[field_name] != default_value:
        warnings.append(
            f'⚠️  Custom {field_name} "{config[field_name]}" will be ignored. '
            f'Using standard directory: "{default_value}"'
        )
        config[field_name] = default_value
    else:
        config[field_name] = default_value

    return warnings


# ============================================================================
# MAIN VALIDATION FUNCTIONS - Orchestrate validation for each config type
# ============================================================================

def validate_cicd_migration_config(config: dict) -> Dict[str, Any]:
    """
    Validate CI/CD Migration configuration

    Args:
        config: Raw configuration dictionary

    Returns:
        Validated configuration dictionary with normalized values

    Raises:
        ValueError: If validation fails with detailed error message
    """
    errors = []
    warnings = []

    try:
        # Required fields
        required_fields = [
            'ProjectName',
            'IICS_SRC_username', 'IICS_SRC_password', 'IICS_SRC_region',
            'IICS_TGT_username', 'IICS_TGT_password', 'IICS_TGT_region',
            'PreMigration_Tag', 'PostMigration_Tag',
            'Git_Repository_URL', 'Git_config_useremail', 'Git_config_username',
            'Git_password', 'Git_SRC_Branch', 'Git_TGT_Branch',
            'Publish'
        ]

        for field in required_fields:
            try:
                validate_required_field(config, field)
            except ValueError as e:
                errors.append(str(e))

        if errors:
            raise ValueError('\n'.join(errors))

        # Type and format validations
        validate_string_field(config, 'ProjectName', min_length=1)
        validate_project_name(config)

        validate_string_field(config, 'IICS_SRC_username', min_length=1)
        validate_string_field(config, 'IICS_SRC_password', min_length=1)
        validate_region(config, 'IICS_SRC_region')

        validate_string_field(config, 'IICS_TGT_username', min_length=1)
        validate_string_field(config, 'IICS_TGT_password', min_length=1)
        validate_region(config, 'IICS_TGT_region')

        validate_array_field(config, 'PreMigration_Tag', min_length=1)
        validate_tags(config, 'PreMigration_Tag')

        validate_array_field(config, 'PostMigration_Tag', min_length=1, max_length=1)
        validate_tags(config, 'PostMigration_Tag')

        validate_https_url(config, 'Git_Repository_URL')
        validate_email(config, 'Git_config_useremail')
        validate_string_field(config, 'Git_config_username', min_length=2)
        validate_string_field(config, 'Git_password', min_length=1)

        validate_git_branch(config, 'Git_SRC_Branch')
        validate_git_branch(config, 'Git_TGT_Branch')

        validate_integer_field(config, 'Publish', min_val=0, max_val=1)

        # Cross-field validations
        validate_source_not_equal_target(
            config,
            'IICS_SRC_username',
            'IICS_TGT_username',
            'Source and target IICS usernames cannot be the same. Cannot migrate to the same organization.'
        )

        validate_source_not_equal_target(
            config,
            'Git_SRC_Branch',
            'Git_TGT_Branch',
            'Source and target Git branches cannot be the same. Cannot cherry-pick from a branch to itself.'
        )

        # Handle directory fields
        dir_warnings = warn_and_override_directory(config, 'logFileDir', 'Logs')
        warnings.extend(dir_warnings)

        if 'reportFileDir' in config and config['reportFileDir'] != 'Reports':
            config['reportFileDir'] = 'Reports'

        result = {
            'valid': True,
            'config': config,
            'warnings': warnings
        }

        return result

    except ValueError as e:
        raise ValueError(f"Configuration validation failed:\n{str(e)}")


def validate_pre_migration_config(config: dict) -> Dict[str, Any]:
    """Validate Pre-Migration configuration"""
    errors = []
    warnings = []

    try:
        # Required fields
        required_fields = [
            'ProjectName',
            'IICS_SRC_username', 'IICS_SRC_password', 'IICS_SRC_region',
            'IICS_TGT_username', 'IICS_TGT_password', 'IICS_TGT_region',
            'PreMigration_Tag'
        ]

        for field in required_fields:
            try:
                validate_required_field(config, field)
            except ValueError as e:
                errors.append(str(e))

        if errors:
            raise ValueError('\n'.join(errors))

        # Validations
        validate_string_field(config, 'ProjectName', min_length=1)
        validate_project_name(config)

        validate_region(config, 'IICS_SRC_region')
        validate_region(config, 'IICS_TGT_region')

        validate_array_field(config, 'PreMigration_Tag', min_length=1)
        validate_tags(config, 'PreMigration_Tag')

        # Handle directories
        dir_warnings = warn_and_override_directory(config, 'logFileDir', 'Logs')
        warnings.extend(dir_warnings)

        dir_warnings = warn_and_override_directory(config, 'reportFileDir', 'Reports')
        warnings.extend(dir_warnings)

        return {
            'valid': True,
            'config': config,
            'warnings': warnings
        }

    except ValueError as e:
        raise ValueError(f"❌ Configuration validation failed:\n{str(e)}")


def validate_post_migration_config(config: dict) -> Dict[str, Any]:
    """Validate Post-Migration configuration"""
    errors = []
    warnings = []

    try:
        # Required fields
        required_fields = [
            'ProjectName',
            'IICS_TGT_username', 'IICS_TGT_password', 'IICS_TGT_region',
            'PostMigration_Tag'
        ]

        for field in required_fields:
            try:
                validate_required_field(config, field)
            except ValueError as e:
                errors.append(str(e))

        if errors:
            raise ValueError('\n'.join(errors))

        # Validations
        validate_string_field(config, 'ProjectName', min_length=1)
        validate_project_name(config)

        validate_region(config, 'IICS_TGT_region')

        validate_array_field(config, 'PostMigration_Tag', min_length=1, max_length=1)
        validate_tags(config, 'PostMigration_Tag')

        # Handle directories
        dir_warnings = warn_and_override_directory(config, 'logFileDir', 'Logs')
        warnings.extend(dir_warnings)

        dir_warnings = warn_and_override_directory(config, 'reportFileDir', 'Reports')
        warnings.extend(dir_warnings)

        return {
            'valid': True,
            'config': config,
            'warnings': warnings
        }

    except ValueError as e:
        raise ValueError(f"❌ Configuration validation failed:\n{str(e)}")


def validate_config(config_data: dict, config_type: str = 'cicd') -> Dict[str, Any]:
    """
    Main entry point for configuration validation

    Args:
        config_data: Raw configuration dictionary
        config_type: Type of config - 'cicd', 'pre', or 'post'

    Returns:
        Dictionary with:
            - valid: True if validation passed
            - config: Validated and normalized configuration
            - warnings: List of warning messages

    Raises:
        ValueError: If validation fails with detailed error message
    """
    if config_type == 'cicd':
        return validate_cicd_migration_config(config_data)
    elif config_type == 'pre':
        return validate_pre_migration_config(config_data)
    elif config_type == 'post':
        return validate_post_migration_config(config_data)
    else:
        raise ValueError(f"Unknown config type: {config_type}. Must be 'cicd', 'pre', or 'post'")
