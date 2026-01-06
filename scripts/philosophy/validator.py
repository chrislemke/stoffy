"""
Philosophy Repository Validator

Rule-based validation for the philosophy knowledge repository.
Enforces naming conventions, date formats, status values, themes, and frontmatter requirements.
"""

import re
from typing import Tuple, List


# Valid values for constrained fields
VALID_THEMES = [
    'consciousness',
    'existence',
    'free_will',
    'knowledge',
    'life_meaning',
    'morality'
]

VALID_STATUSES = [
    'seed',
    'exploring',
    'developing',
    'crystallized',
    'challenged',
    'integrated',
    'archived'
]

# Valid source statuses (different from thought statuses)
VALID_SOURCE_STATUSES = [
    'to_read',
    'reading',
    'read',
    'reference'
]

# Required frontmatter fields by content type
REQUIRED_FIELDS = {
    'thought': ['title', 'theme', 'status', 'started'],
    'thinker': ['name', 'type', 'era', 'traditions', 'themes', 'tags'],
    'source': ['title', 'type', 'author', 'themes', 'tags']
}


def validate_filename(name: str) -> Tuple[bool, str]:
    """
    Validate that a filename follows lowercase_with_underscores convention.

    Rules:
    - Must be lowercase letters, numbers, and underscores only
    - No spaces, hyphens, or special characters
    - No consecutive underscores
    - Cannot start or end with underscore

    Args:
        name: The filename to validate (without extension)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Filename cannot be empty"

    # Check for uppercase letters
    if name != name.lower():
        return False, f"Filename must be lowercase: '{name}' contains uppercase characters"

    # Check for spaces
    if ' ' in name:
        return False, f"Filename cannot contain spaces: '{name}'"

    # Check for hyphens
    if '-' in name:
        return False, f"Filename should use underscores, not hyphens: '{name}'"

    # Check for valid characters (lowercase, numbers, underscores)
    pattern = r'^[a-z0-9_]+$'
    if not re.match(pattern, name):
        invalid_chars = set(re.findall(r'[^a-z0-9_]', name))
        return False, f"Filename contains invalid characters: {invalid_chars}"

    # Check for consecutive underscores
    if '__' in name:
        return False, f"Filename cannot contain consecutive underscores: '{name}'"

    # Check start/end with underscore
    if name.startswith('_'):
        return False, f"Filename cannot start with underscore: '{name}'"
    if name.endswith('_'):
        return False, f"Filename cannot end with underscore: '{name}'"

    return True, ""


def validate_date(date_str: str) -> Tuple[bool, str]:
    """
    Validate that a date string follows ISO 8601 format (YYYY-MM-DD).

    Args:
        date_str: The date string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not date_str:
        return False, "Date cannot be empty"

    # Remove quotes if present (common in YAML)
    date_str = date_str.strip('"\'')

    # Check basic format
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        return False, f"Date must be in ISO 8601 format (YYYY-MM-DD): '{date_str}'"

    # Parse components
    try:
        year, month, day = map(int, date_str.split('-'))
    except ValueError:
        return False, f"Invalid date format: '{date_str}'"

    # Validate year range (reasonable bounds)
    if year < 1900 or year > 2100:
        return False, f"Year out of reasonable range (1900-2100): {year}"

    # Validate month
    if month < 1 or month > 12:
        return False, f"Invalid month: {month}"

    # Days per month (accounting for leap years)
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    # Leap year check
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    if is_leap:
        days_in_month[2] = 29

    # Validate day
    if day < 1 or day > days_in_month[month]:
        return False, f"Invalid day {day} for month {month}"

    return True, ""


def validate_thought_status(status: str) -> Tuple[bool, str]:
    """
    Validate that a thought status is one of the valid lifecycle stages.

    Valid statuses: seed, exploring, developing, crystallized, challenged, integrated, archived

    Args:
        status: The status value to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not status:
        return False, "Status cannot be empty"

    status = status.lower().strip()

    if status not in VALID_STATUSES:
        return False, f"Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}"

    return True, ""


def validate_theme(theme: str) -> Tuple[bool, str]:
    """
    Validate that a theme is one of the valid philosophical categories.

    Valid themes: consciousness, existence, free_will, knowledge, life_meaning, morality

    Args:
        theme: The theme value to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not theme:
        return False, "Theme cannot be empty"

    theme = theme.lower().strip()

    if theme not in VALID_THEMES:
        return False, f"Invalid theme '{theme}'. Must be one of: {', '.join(VALID_THEMES)}"

    return True, ""


def validate_source_status(status: str) -> Tuple[bool, str]:
    """
    Validate that a source status is one of the valid reading statuses.

    Valid statuses: to_read, reading, read, reference

    Args:
        status: The status value to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not status:
        return False, "Source status cannot be empty"

    status = status.lower().strip()

    if status not in VALID_SOURCE_STATUSES:
        return False, f"Invalid source status '{status}'. Must be one of: {', '.join(VALID_SOURCE_STATUSES)}"

    return True, ""


def validate_frontmatter(frontmatter: dict, content_type: str) -> Tuple[bool, List[str]]:
    """
    Validate that frontmatter contains all required fields for the content type.

    Args:
        frontmatter: Dictionary of frontmatter fields
        content_type: One of 'thought', 'thinker', or 'source'

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors = []

    if not frontmatter:
        return False, ["Frontmatter is empty or missing"]

    if not isinstance(frontmatter, dict):
        return False, ["Frontmatter must be a dictionary"]

    content_type = content_type.lower().strip()

    if content_type not in REQUIRED_FIELDS:
        return False, [f"Unknown content type '{content_type}'. Must be one of: {', '.join(REQUIRED_FIELDS.keys())}"]

    required = REQUIRED_FIELDS[content_type]

    # Check for missing required fields
    missing = [field for field in required if field not in frontmatter]
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    # Validate specific fields if present
    if 'theme' in frontmatter:
        valid, err = validate_theme(frontmatter['theme'])
        if not valid:
            errors.append(err)

    if 'themes' in frontmatter and isinstance(frontmatter['themes'], list):
        for theme in frontmatter['themes']:
            valid, err = validate_theme(theme)
            if not valid:
                errors.append(err)

    if 'status' in frontmatter:
        # Use appropriate status validator based on content type
        if content_type == 'source':
            valid, err = validate_source_status(frontmatter['status'])
        else:
            valid, err = validate_thought_status(frontmatter['status'])
        if not valid:
            errors.append(err)

    if 'started' in frontmatter:
        valid, err = validate_date(str(frontmatter['started']))
        if not valid:
            errors.append(err)

    if 'last_updated' in frontmatter:
        valid, err = validate_date(str(frontmatter['last_updated']))
        if not valid:
            errors.append(err)

    return len(errors) == 0, errors


def _extract_frontmatter(content: str) -> Tuple[dict, str]:
    """
    Extract YAML frontmatter from markdown content.

    Args:
        content: Full markdown file content

    Returns:
        Tuple of (frontmatter_dict, remaining_content)
    """
    import yaml

    if not content.startswith('---'):
        return {}, content

    # Find the closing ---
    lines = content.split('\n')
    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == '---':
            end_idx = i
            break

    if end_idx == -1:
        return {}, content

    frontmatter_text = '\n'.join(lines[1:end_idx])
    remaining = '\n'.join(lines[end_idx + 1:])

    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return frontmatter, remaining


def validate_thought(content: str) -> Tuple[bool, List[str]]:
    """
    Validate a thought file's content and structure.

    Checks:
    - Required frontmatter fields (title, theme, status, started)
    - Valid theme value
    - Valid status value
    - Valid date format

    Args:
        content: Full markdown file content including frontmatter

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors = []

    if not content:
        return False, ["Content is empty"]

    frontmatter, _ = _extract_frontmatter(content)

    if not frontmatter:
        errors.append("Missing or invalid YAML frontmatter")
        return False, errors

    valid, fm_errors = validate_frontmatter(frontmatter, 'thought')
    errors.extend(fm_errors)

    return len(errors) == 0, errors


def validate_thinker(content: str) -> Tuple[bool, List[str]]:
    """
    Validate a thinker profile file's content and structure.

    Checks:
    - Required frontmatter fields (name, type, era, traditions, themes, tags)
    - Valid theme values in themes list

    Args:
        content: Full markdown file content including frontmatter

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors = []

    if not content:
        return False, ["Content is empty"]

    frontmatter, _ = _extract_frontmatter(content)

    if not frontmatter:
        errors.append("Missing or invalid YAML frontmatter")
        return False, errors

    valid, fm_errors = validate_frontmatter(frontmatter, 'thinker')
    errors.extend(fm_errors)

    return len(errors) == 0, errors


def validate_source(content: str) -> Tuple[bool, List[str]]:
    """
    Validate a source file's content and structure.

    Checks:
    - Required frontmatter fields (title, type, author, themes, tags)
    - Valid theme values in themes list

    Args:
        content: Full markdown file content including frontmatter

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors = []

    if not content:
        return False, ["Content is empty"]

    frontmatter, _ = _extract_frontmatter(content)

    if not frontmatter:
        errors.append("Missing or invalid YAML frontmatter")
        return False, errors

    valid, fm_errors = validate_frontmatter(frontmatter, 'source')
    errors.extend(fm_errors)

    return len(errors) == 0, errors


# Convenience functions for batch validation

def validate_themes_list(themes: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate a list of themes.

    Args:
        themes: List of theme strings

    Returns:
        Tuple of (all_valid, list_of_error_messages)
    """
    errors = []
    for theme in themes:
        valid, err = validate_theme(theme)
        if not valid:
            errors.append(err)
    return len(errors) == 0, errors


def get_valid_themes() -> List[str]:
    """Return the list of valid themes."""
    return VALID_THEMES.copy()


def get_valid_statuses() -> List[str]:
    """Return the list of valid thought statuses."""
    return VALID_STATUSES.copy()


def get_valid_source_statuses() -> List[str]:
    """Return the list of valid source statuses."""
    return VALID_SOURCE_STATUSES.copy()


def get_required_fields(content_type: str) -> List[str]:
    """
    Get required frontmatter fields for a content type.

    Args:
        content_type: One of 'thought', 'thinker', or 'source'

    Returns:
        List of required field names, or empty list if unknown type
    """
    return REQUIRED_FIELDS.get(content_type.lower(), []).copy()


if __name__ == '__main__':
    # Simple test when run directly
    print("Philosophy Repository Validator")
    print("=" * 40)
    print(f"Valid themes: {', '.join(VALID_THEMES)}")
    print(f"Valid statuses: {', '.join(VALID_STATUSES)}")
    print()

    # Test filename validation
    test_filenames = [
        ('good_filename', True),
        ('also_good_123', True),
        ('Bad_Name', False),
        ('has spaces', False),
        ('has-hyphens', False),
        ('double__underscore', False),
        ('_starts_underscore', False),
    ]

    print("Filename validation tests:")
    for name, expected in test_filenames:
        valid, err = validate_filename(name)
        status = "PASS" if valid == expected else "FAIL"
        print(f"  [{status}] {name}: valid={valid}")
        if err:
            print(f"         Error: {err}")

    print()

    # Test date validation
    test_dates = [
        ('2025-12-26', True),
        ('2025-02-29', False),  # 2025 is not a leap year
        ('2024-02-29', True),   # 2024 is a leap year
        ('2025-13-01', False),  # Invalid month
        ('12-26-2025', False),  # Wrong format
    ]

    print("Date validation tests:")
    for date, expected in test_dates:
        valid, err = validate_date(date)
        status = "PASS" if valid == expected else "FAIL"
        print(f"  [{status}] {date}: valid={valid}")
        if err:
            print(f"         Error: {err}")
