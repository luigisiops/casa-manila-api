"""
Validation utilities for order-related data.
"""

import re
from django.core.validators import EmailValidator as DjangoEmailValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError


def validate_email_format(email):
    """
    Validate that the email follows a valid format using Django's EmailValidator.
    Raises ValidationError if invalid.
    """
    if not email:
        return None

    validator = DjangoEmailValidator()
    try:
        validator(email)
    except DjangoValidationError as exc:
        raise ValidationError(
            {"search": f"Invalid email format: {email}"}
        ) from exc
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
