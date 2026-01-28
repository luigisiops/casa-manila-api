"""
Validation utilities for order-related data.
"""

import re
from rest_framework.exceptions import ValidationError


def validate_email_format(email):
    """
    Validate that the email follows a basic valid format.
    Raises ValidationError if invalid.
    """
    if not email:
        return None

    # Basic email regex: alphanumeric + some special chars @ alphanumeric + domain
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError(
            {"search": f"Invalid email format: {email}"}
        )
    return email


def validate_phone_format(phone):
    """
    Validate that the phone number contains only digits and common separators.
    Raises ValidationError if invalid.
    """
    if not phone:
        return None

    # Allow only digits, spaces, hyphens, parentheses, and plus sign
    phone_pattern = r'^[0-9\s\-\(\)\+]+$'
    if not re.match(phone_pattern, phone):
        raise ValidationError(
            {"search": f"Invalid phone number format: {phone}"}
        )

    # Ensure there's at least some digits
    if not re.search(r'\d', phone):
        raise ValidationError(
            {"search": f"Phone number must contain digits: {phone}"}
        )

    return phone
