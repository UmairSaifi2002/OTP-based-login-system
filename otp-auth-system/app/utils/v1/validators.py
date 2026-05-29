"""
Input Validators – The Three Gatekeepers

This module contains all validation logic for:
- Email address format and deliverability basics
- Country calling codes
- Phone number format per country

Each function raises ValueError with a clear message if validation fails.
The caller (AuthManager) catches these and turns them into HTTP 400 errors.
"""


import re
from typing import Optional

import phonenumbers
from phonenumbers import NumberParseException

# --------------------------------------------------------
# 1. EMAIL VALIDATION
# --------------------------------------------------------

# Basic email regex – good enough for catching obvious garbage
# Pydantic's EmailStr already does most of this, but we add one extra:
# we reject obviously disposable domains at the manager level.
# Here we just check structure again, but we'll also do a quick MX check concept.

# For now, we trust EmailStr for format. We'll add a simple domain blocklist later if needed.
# This function can be extended.
def validate_email(email: str) -> None:
    """
    Validates email format (redundant with EmailStr but kept for consistency).
    Raises ValueError if email is present but malformed.
    """
    if email is None:
        return
    
    # Pydantic already validated EmailStr, so this is just a safety net.
    # We'll check that it contains '@' and a domain part with a dot.
    if '@' not in email or '.' not in email.split('@')[1]:
        raise ValueError("Invalid email format")
    

# --------------------------------------------------------
# 2. COUNTRY CODE VALIDATION
# --------------------------------------------------------

# We'll map from dialing code to country code (ISO 3166-1 alpha-2) for validation.
# The phonenumbers library can give us valid country codes.
VALID_COUNTRY_CODES = {
    "+1", "+7", "+20", "+27", "+30", "+31", "+32", "+33", "+34", "+36", "+39",
    "+40", "+41", "+43", "+44", "+45", "+46", "+47", "+48", "+49", "+51", "+52",
    "+53", "+54", "+55", "+56", "+57", "+58", "+60", "+61", "+62", "+63", "+64",
    "+65", "+66", "+81", "+82", "+84", "+86", "+90", "+91", "+92", "+93", "+94",
    "+95", "+98", "+212", "+213", "+216", "+218", "+220", "+221", "+222", "+223",
    "+224", "+225", "+226", "+227", "+228", "+229", "+230", "+231", "+232", "+233",
    "+234", "+235", "+236", "+237", "+238", "+239", "+240", "+241", "+242", "+243",
    "+244", "+245", "+246", "+247", "+248", "+249", "+250", "+251", "+252", "+253",
    "+254", "+255", "+256", "+257", "+258", "+260", "+261", "+262", "+263", "+264",
    "+265", "+266", "+267", "+268", "+269", "+290", "+291", "+297", "+298", "+299",
    "+350", "+351", "+352", "+353", "+354", "+355", "+356", "+357", "+358", "+359",
    "+370", "+371", "+372", "+373", "+374", "+375", "+376", "+377", "+378", "+380",
    "+381", "+382", "+383", "+385", "+386", "+387", "+389", "+420", "+421", "+423",
    "+500", "+501", "+502", "+503", "+504", "+505", "+506", "+507", "+508", "+509",
    "+590", "+591", "+592", "+593", "+594", "+595", "+596", "+597", "+598", "+599",
    "+670", "+672", "+673", "+674", "+675", "+676", "+677", "+678", "+679", "+680",
    "+681", "+682", "+683", "+685", "+686", "+687", "+688", "+689", "+690", "+691",
    "+692", "+850", "+852", "+853", "+855", "+856", "+872", "+878", "+880", "+886",
    "+960", "+961", "+962", "+963", "+964", "+965", "+966", "+967", "+968", "+970",
    "+971", "+972", "+973", "+974", "+975", "+976", "+977", "+992", "+993", "+994",
    "+995", "+996", "+998"
}

def validate_country_code(country_code: str) -> None:
    """
    Validates that a country code string is a known international dialing code.
    Must start with '+' followed by digits.
    Raises ValueError if invalid.
    """
    if country_code is None:
        return
    if not re.match(r'^\+\d{1,4}$', country_code):
        raise ValueError(f"Invalid country code format: {country_code}. Must be like '+91'.")
    if country_code not in VALID_COUNTRY_CODES:
        raise ValueError(f"Unsupported Country Code: {country_code}. Please provide a valid international dialing code.")



# --------------------------------------------------------
# 3. PHONE NUMBER VALIDATION (per country)
# --------------------------------------------------------
def validate_phone_number(country_code : Optional[str], phone_number: Optional[str]) -> None:
    """
    Validates a national phone number, optionally against a country code.
    Uses Google's phonenumbers library.
    
    If country_code is provided, we parse as (country_code + phone) and check validity.
    If no country_code, we try to parse the raw number but it's likely invalid.
    
    Raises ValueError if the phone number is not valid for the given country.
    """
    if phone_number is None:
        return
    
    # Basic check: must be digits only, possibly with leading 0 removed.
    if not re.match(r'^\d{4,15}$', phone_number):
        raise ValueError("Phone number must contain only digits, 4-15 characters.")
    
    if country_code:
        # Combine and Parse
        full_number_str = f"{country_code}{phone_number}"
        try:
            number = phonenumbers.parse(full_number_str, None) # We provide None because we have the country code in the number itself
        except NumberParseException as e:
            raise ValueError(f"Invalid phone number format: {e}")
        if not phonenumbers.is_valid_number(number):
            raise ValueError(f"Phone number '{phone_number}' is not valid for country code {country_code}.")
    
    else:
        # If no country code, we can't reliably validate, but we could try parsing as international.
        # For safety, require country code.
        raise ValueError("Country code is required to validate phone number. Please provide a valid country code.")


# --------------------------------------------------------
# 4. CROSS-FIELD VALIDATION (The Guards Talk to Each Other)
# --------------------------------------------------------
def validate_request_inputs(
        email: Optional[str],
        country_code: Optional[str],
        phone_number: Optional[str]
) -> None:
    """
    Comprehensive validation of all inputs.
    Ensures at least one contact method is provided,
    and that phone fields are consistently filled.
    
    Raises ValueError with a user-friendly message if anything fails.
    """
    # At least one of email or phone must be present
    if not email and not phone_number:
        raise ValueError("Either email or phone_number is required.")
    
    # If phone number is provided, country code must also be provided
    if phone_number and not country_code:
        raise ValueError("Country code is required when phone number is provided.")
    
    if country_code and not phone_number:
        raise ValueError("Phone number is required when country code is provided.")

    # Validate each field
    validate_email(email)
    validate_country_code(country_code)
    validate_phone_number(country_code, phone_number)









