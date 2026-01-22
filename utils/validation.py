"""Input validation utilities for the tax return application.

This module provides functions to sanitize and validate user input
to prevent XSS and other input-related vulnerabilities.
"""
import html
import re
from typing import Optional

# Maximum lengths for various fields
MAX_CATEGORY_LENGTH = 50
MAX_CLIENT_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500
MAX_SETTING_KEY_LENGTH = 50
MAX_SETTING_VALUE_LENGTH = 200


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


def sanitize_text(text: Optional[str], max_length: int = 500, field_name: str = "フィールド") -> str:
    """Sanitize text input by escaping HTML and limiting length.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        field_name: Name of the field for error messages

    Returns:
        Sanitized text string

    Raises:
        ValidationError: If text exceeds max length after sanitization
    """
    if text is None:
        return ''

    # Convert to string if not already
    text = str(text).strip()

    # Escape HTML entities to prevent XSS
    text = html.escape(text)

    # Check length
    if len(text) > max_length:
        raise ValidationError(f"{field_name}は{max_length}文字以内で入力してください")

    return text


def sanitize_category(category: Optional[str]) -> str:
    """Sanitize category input.

    Args:
        category: Category name

    Returns:
        Sanitized category string

    Raises:
        ValidationError: If validation fails
    """
    if not category or not category.strip():
        raise ValidationError("カテゴリは必須です")

    return sanitize_text(category, MAX_CATEGORY_LENGTH, "カテゴリ")


def sanitize_client(client: Optional[str]) -> str:
    """Sanitize client name input.

    Args:
        client: Client name

    Returns:
        Sanitized client string
    """
    return sanitize_text(client, MAX_CLIENT_LENGTH, "取引先")


def sanitize_description(description: Optional[str]) -> str:
    """Sanitize description input.

    Args:
        description: Description text

    Returns:
        Sanitized description string
    """
    return sanitize_text(description, MAX_DESCRIPTION_LENGTH, "摘要")


def validate_record_type(record_type: str) -> str:
    """Validate record type is either 'income' or 'expense'.

    Args:
        record_type: Record type value

    Returns:
        Validated record type

    Raises:
        ValidationError: If record type is invalid
    """
    valid_types = ('income', 'expense')
    if record_type not in valid_types:
        raise ValidationError(f"種別は{', '.join(valid_types)}のいずれかである必要があります")
    return record_type


def validate_currency(currency: str) -> str:
    """Validate currency code.

    Args:
        currency: Currency code

    Returns:
        Validated currency code

    Raises:
        ValidationError: If currency is invalid
    """
    valid_currencies = ('JPY', 'USD')
    if currency not in valid_currencies:
        raise ValidationError(f"通貨は{', '.join(valid_currencies)}のいずれかである必要があります")
    return currency


def validate_amount(amount, field_name: str = "金額") -> float:
    """Validate and convert amount to float.

    Args:
        amount: Amount value (can be string, int, or float)
        field_name: Name of the field for error messages

    Returns:
        Validated amount as float

    Raises:
        ValidationError: If amount is invalid
    """
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name}は数値で入力してください")

    if amount < 0:
        raise ValidationError(f"{field_name}は0以上の値を入力してください")

    return amount


def validate_rate(rate, field_name: str = "率") -> float:
    """Validate percentage rate (0-100).

    Args:
        rate: Rate value
        field_name: Name of the field for error messages

    Returns:
        Validated rate as float

    Raises:
        ValidationError: If rate is invalid
    """
    try:
        rate = float(rate)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name}は数値で入力してください")

    if rate < 0 or rate > 100:
        raise ValidationError(f"{field_name}は0〜100の範囲で入力してください")

    return rate


def validate_date(date_str: Optional[str]) -> str:
    """Validate date string format (YYYY-MM-DD).

    Args:
        date_str: Date string

    Returns:
        Validated date string

    Raises:
        ValidationError: If date format is invalid
    """
    if not date_str:
        raise ValidationError("日付は必須です")

    # Check format with regex
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise ValidationError("日付はYYYY-MM-DD形式で入力してください")

    # Parse to validate actual date
    from datetime import datetime
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValidationError("無効な日付です")

    return date_str


def validate_filename(filename: str) -> str:
    """Validate and sanitize filename.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename

    Raises:
        ValidationError: If filename is invalid
    """
    if not filename:
        raise ValidationError("ファイル名は必須です")

    # Remove path components
    filename = filename.replace('\\', '/').split('/')[-1]

    # Check for dangerous characters
    if re.search(r'[<>:"|?*\x00-\x1f]', filename):
        raise ValidationError("ファイル名に使用できない文字が含まれています")

    # Limit length
    if len(filename) > 255:
        raise ValidationError("ファイル名が長すぎます")

    return filename


def validate_file_extension(filename: str, allowed_extensions: set) -> str:
    """Validate file extension.

    Args:
        filename: Filename to check
        allowed_extensions: Set of allowed extensions (e.g., {'.pdf', '.jpg'})

    Returns:
        The file extension (lowercase)

    Raises:
        ValidationError: If extension is not allowed
    """
    import os
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_extensions:
        allowed_str = ', '.join(sorted(allowed_extensions))
        raise ValidationError(f"許可されていないファイル形式です。対応形式: {allowed_str}")

    return ext
