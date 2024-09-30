import pandas as pd
import hashlib
import argparse
import logging
import phonenumbers
from phonenumbers import (
    parse, is_valid_number, format_number, PhoneNumberFormat,
    NumberParseException, COUNTRY_CODE_TO_REGION_CODE
)
import re
import openpyxl
from pathlib import Path
from enum import Enum, auto
from typing import List, Tuple, Optional, Dict
from dateutil import parser as date_parser
from collections import Counter
import json
import difflib

# Constants
EMAIL_COL = 'email'
PHONE_COL = 'phone'
ALT_PHONE_COL = 'alternate phone'
NAME_COLS = ['first name', 'last name', 'country', 'zip']
DATE_COL = 'date'
CONSENT_COL = 'consent'
YEAR_COL = 'year'
EXPECTED_COLUMNS = [EMAIL_COL, PHONE_COL, ALT_PHONE_COL] + NAME_COLS + [DATE_COL, CONSENT_COL]

# Prefixes and suffixes for multiple languages (abbreviated versions)
PREFIXES = [
    'mr', 'mrs', 'ms', 'miss', 'dr', 'prof', 'rev',  # English
    'hr', 'fr', 'frl',  # German
    'm', 'mme', 'mlle', 'dr',  # French
    'sig', 'sig.ra', 'sig.na', 'dott',  # Italian
    'sr', 'sra', 'srta', 'dr',  # Spanish
    'sr', 'sra', 'srta', 'dr',  # Portuguese
    'dhr', 'mevr', 'mej',  # Dutch
]

SUFFIXES = [
    'jr', 'sr', 'ii', 'iii', 'iv', 'v',  # English
    'jr', 'sr',  # Multiple languages
    'filho', 'filha',  # Portuguese
    'hijo', 'hija',  # Spanish
]

class MatchingType(Enum):
    EMAIL = auto()
    PHONE = auto()
    MAILING_ADDRESS = auto()
    COMBINED = auto()

def counted_debug(message):
    if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
        if not hasattr(counted_debug, "counter"):
            counted_debug.counter = Counter()
        counted_debug.counter[message] += 1

def print_debug_summary():
    if hasattr(counted_debug, "counter"):
        print("\nDebug message summary:")
        for message, count in counted_debug.counter.items():
            print(f"  • {message}: {count} occurrences")
        print()

def setup_logging(log_level: str) -> None:
    """Set up logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}. Defaulting to ERROR.")
        numeric_level = logging.ERROR
    logging.basicConfig(level=numeric_level, format='%(levelname)s: %(message)s')

def hash_data(value: str) -> str:
    """Hash a given string using SHA-256."""
    if isinstance(value, str):
        return hashlib.sha256(value.strip().lower().encode()).hexdigest()
    return value

def clean_and_format_phone(phone: Optional[str], keep_formatted: bool = False) -> Tuple[Optional[str], bool]:
    """Clean and format phone numbers, optionally keeping formatted but unvalidated numbers."""
    if pd.isna(phone) or not isinstance(phone, str) or not phone.strip():
        return None, False

    # Remove all non-digit characters except '+'
    phone = ''.join(char for char in phone if char.isdigit() or char == '+')

    # Handle cases with multiple '+' or '00' at the start
    phone = phone.lstrip('+')
    while phone.startswith('00'):
        phone = phone[2:]

    # Add '+' at the beginning if it's not there
    if not phone.startswith('+'):
        phone = '+' + phone

    # Try to parse the number as is
    try:
        parsed_number = parse(phone, None)
        if is_valid_number(parsed_number):
            formatted = format_number(parsed_number, PhoneNumberFormat.E164)
            logging.debug(f"Successfully formatted phone number: {phone} -> {formatted}")
            return formatted, True
    except NumberParseException:
        pass

    # If parsing failed, try removing the leading '0' if present
    if phone.startswith('+0'):
        phone = '+' + phone[2:]
        try:
            parsed_number = parse(phone, None)
            if is_valid_number(parsed_number):
                formatted = format_number(parsed_number, PhoneNumberFormat.E164)
                logging.debug(f"Successfully formatted phone number after removing leading 0: {phone} -> {formatted}")
                return formatted, True
        except NumberParseException:
            pass

    # If still not valid, try to determine the country code
    for code_length in range(1, 4):  # Country codes can be 1 to 3 digits
        try:
            country_code = int(phone[1:1+code_length])
            if country_code in COUNTRY_CODE_TO_REGION_CODE:
                remaining_number = phone[1+code_length:]
                test_number = f"+{country_code}{remaining_number}"
                parsed_number = parse(test_number, None)
                if is_valid_number(parsed_number):
                    formatted = format_number(parsed_number, PhoneNumberFormat.E164)
                    logging.debug(f"Successfully formatted phone number after country code detection: {phone} -> {formatted}")
                    return formatted, True
        except (ValueError, NumberParseException):
            continue

    # If the number is not validated but appears to be in the correct format
    if keep_formatted and re.match(r'^\+\d{10,15}$', phone):
        logging.info(f"Keeping unvalidated but correctly formatted phone number: {phone}")
        return phone, False

    logging.info(f"Invalid phone number detected and excluded: {phone}")
    return None, False

def clean_and_validate_email(email: Optional[str]) -> Optional[str]:
    """Clean and validate email addresses."""
    if not isinstance(email, str):
        return None

    email = email.strip()
    # Improved regex for email validation
    regex = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
    if re.match(regex, email):
        return email  # Return valid email
    else:
        counted_debug(f"Invalid email detected: {email}")
        return None  # Invalid email

def create_country_dict() -> Dict[str, str]:
    country_dict = {}
    try:
        with open('country_names.json', 'r', encoding='utf-8') as f:
            country_data = json.load(f)

        for iso_2, data in country_data.items():
            # Add names
            for name in data['names']:
                country_dict[name.lower()] = iso_2

            # Add codes
            for code in data['codes']:
                country_dict[code.lower()] = iso_2

        logging.debug(f"Created country dictionary with {len(country_dict)} entries")

    except FileNotFoundError:
        logging.error("country_names.json file not found. Country dictionary is empty.")

    return country_dict

def validate_name(name: Optional[str]) -> Optional[str]:
    """Validate and clean first and last names."""
    if not isinstance(name, str):
        return None

    name = name.strip().lower()

    # Remove prefixes and suffixes
    name_parts = name.split()
    name_parts = [part for part in name_parts if part not in PREFIXES and part not in SUFFIXES]

    if not name_parts:
        return None

    # Allow letters, spaces, hyphens, and accents
    if all(re.match(r"^[a-zà-ÿ\s\-]+$", part, re.IGNORECASE) for part in name_parts):
        return ' '.join(name_parts).title()
    else:
        counted_debug(f"Invalid name detected: {name}")
        return None

def validate_country(country: Optional[str]) -> Optional[str]:
    """Validate and convert country to ISO 2-letter code."""
    if not isinstance(country, str):
        logging.debug(f"Country is not a string: {country}")
        return None

    country = country.strip().lower()
    logging.debug(f"Validating country: {country}")

    # Check if it's in our dictionary
    if country in COUNTRY_DICT:
        logging.debug(f"Country found in dictionary: {country} -> {COUNTRY_DICT[country]}")
        return COUNTRY_DICT[country]

    # If not found, try to find a close match
    close_matches = difflib.get_close_matches(country, COUNTRY_DICT.keys(), n=1, cutoff=0.8)
    if close_matches:
        logging.debug(f"Close match found for country: {country} -> {close_matches[0]} -> {COUNTRY_DICT[close_matches[0]]}")
        return COUNTRY_DICT[close_matches[0]]

    logging.debug(f"Invalid country detected: {country}")
    return None

def validate_zip(zip_code: Optional[str], country: Optional[str]) -> Optional[str]:
    """Validate zip/postal code."""
    if not isinstance(zip_code, str):
        return None

    zip_code = zip_code.strip().upper()

    # If the zip code is empty after stripping, return None
    if not zip_code:
        return None

    # Accept any non-empty string as a valid zip code
    return zip_code

    # Uncomment the following block if you want to keep some basic validation
    # # Basic format check for common countries
    # if country == 'US' and re.match(r'^\d{5}(-\d{4})?$', zip_code):
    #     return zip_code
    # elif country == 'CA' and re.match(r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$', zip_code):
    #     return zip_code
    # elif country == 'GB' and re.match(r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}$', zip_code):
    #     return zip_code
    # else:
    #     # For other countries, accept any alphanumeric string
    #     if re.match(r'^[A-Z0-9\s-]+$', zip_code):
    #         return zip_code

    # logging.debug(f"Invalid zip code detected: {zip_code} for country {country}")
    # return None

def is_valid_column(df: pd.DataFrame, columns: List[str]) -> bool:
    """Check if all specified columns exist and have at least one non-null value."""
    return all(col.lower() in df.columns and df[col].notnull().any() for col in columns)

def handle_existing_file(file_name: Path, overwrite: bool) -> Path:
    """Handle existing files by overwriting or prompting the user."""
    logging.debug(f"Checking if file exists: {file_name}")
    if file_name.exists():
        logging.debug(f"File already exists: {file_name}")
        if overwrite:
            logging.debug(f"Overwriting existing file: {file_name}")
            return file_name  # Overwrite without confirmation
        while True:
            choice = input(f"File '{file_name}' already exists. Overwrite? (y/n): ").lower()
            if choice == 'y':
                logging.debug(f"User chose to overwrite: {file_name}")
                return file_name
            elif choice == 'n':
                new_file_name = Path(input("Enter a new file name (with .csv extension): "))
                if not new_file_name.suffix:
                    new_file_name = new_file_name.with_suffix('.csv')
                if not new_file_name.exists():
                    logging.debug(f"User entered new file name: {new_file_name}")
                    return new_file_name
                else:
                    print(f"File '{new_file_name}' already exists.")
            else:
                print("Please enter 'y' or 'n'.")
    return file_name

def create_directory(directory_name: str) -> Path:
    """Create a directory with lowercase and hyphens instead of spaces inside the output directory."""
    output_dir = Path("output")
    directory_name = directory_name.lower().replace(" ", "-")
    full_path = output_dir / directory_name
    output_dir.mkdir(exist_ok=True)
    logging.debug(f"Created main output directory: {output_dir}")
    full_path.mkdir(exist_ok=True)
    logging.debug(f"Created directory: {full_path}")
    return full_path

def show_column_info(df: pd.DataFrame) -> None:
    """Display column names, their filled data percentages, and the number of filled rows."""
    total_rows = len(df)
    print(f"\nInput file information (Total rows: {total_rows}):\n")
    for column in df.columns:
        filled_rows = df[column].notnull().sum()
        filled_percentage = (filled_rows / total_rows) * 100
        print(f"  • {column}: {filled_rows} rows ({filled_percentage:.2f}% filled)")
    print()  # Blank line after the bullet points

def extract_year(date: str) -> Optional[int]:
    """Extract year from a date string, regardless of format."""
    try:
        return date_parser.parse(date).year
    except (ValueError, TypeError):
        return None

def process_and_save(df: pd.DataFrame, email_col: str, phone_col: str, alt_phone_col: str, base_file_name: str,
                     directory_name: str, date_col: Optional[str] = None, filter_by_consent: bool = False,
                     hash_enabled: bool = False, overwrite: bool = False,
                     matching_type: MatchingType = None, keep_unvalidated_phones: bool = False) -> Tuple[pd.DataFrame, List[Tuple[str, int]], int, Dict[str, Tuple[int, int, int]]]:
    """Process and save data based on matching type."""
    directory_path = create_directory(directory_name)
    validation_stats = {}

    logging.debug(f"Processing and saving data for matching type: {matching_type}")
    logging.debug(f"Input DataFrame shape: {df.shape}")

    # Validate email
    if email_col in df.columns:
        original_email_count = df[email_col].notnull().sum()
        df[email_col] = df[email_col].apply(clean_and_validate_email)
        valid_email_count = df[email_col].notnull().sum()
        validation_stats[email_col] = (valid_email_count, 0, original_email_count)
        logging.debug(f"Email validation: {valid_email_count} valid out of {original_email_count} original")

    # Validate phone numbers
    phone_columns = [col for col in [phone_col, alt_phone_col] if col in df.columns]
    for col in phone_columns:
        original_count = df[col].notnull().sum()
        df[col], df[f'{col}_validated'] = zip(*df[col].apply(lambda x: clean_and_format_phone(x, keep_unvalidated_phones)))
        valid_count = df[df[f'{col}_validated']].shape[0]
        unvalidated_count = df[(df[col].notnull()) & (~df[f'{col}_validated'])].shape[0]
        validation_stats[col] = (valid_count, unvalidated_count, original_count)
        logging.debug(f"Phone validation for {col}: {valid_count} valid, {unvalidated_count} unvalidated out of {original_count} original")

    # Validate other fields (except zip)
    for col in NAME_COLS:
        if col in df.columns:
            if col in ['first name', 'last name']:
                df[col] = df[col].apply(validate_name)
            elif col == 'country':
                df[col] = df[col].apply(validate_country)
            elif col == 'zip':
                # Don't validate zip, just count non-null values
                pass

            original_count = df[col].notnull().sum()
            valid_count = df[col].notnull().sum()
            validation_stats[col] = (valid_count, 0, original_count)
            logging.debug(f"Validation stats for {col}: {valid_count} valid out of {original_count} original")

    if matching_type == MatchingType.PHONE:
        logging.debug("Processing phone matching...")
        valid_data = pd.DataFrame(columns=[PHONE_COL])
        for col in phone_columns:
            valid_data = pd.concat([valid_data, df[[col]].dropna(subset=[col]).rename(columns={col: PHONE_COL})], ignore_index=True)
        column_header = [PHONE_COL]
        file_suffix = 'phone'
        logging.debug(f"Valid phone numbers: {len(valid_data)} out of {len(df)}")

    elif matching_type == MatchingType.EMAIL:
        logging.debug("Processing email matching...")
        valid_data = df[[email_col]].dropna(subset=[email_col])
        column_header = [EMAIL_COL]
        file_suffix = 'email'
        logging.debug(f"Valid email addresses: {len(valid_data)} out of {len(df)}")

    elif matching_type == MatchingType.MAILING_ADDRESS:
        logging.debug("Processing mailing address matching...")
        required_fields = ['first name', 'last name', 'country', 'zip']
        valid_data = df[NAME_COLS].dropna(subset=required_fields)

        if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
            discarded_rows = df[~df.index.isin(valid_data.index)]
            for idx, row in discarded_rows.iterrows():
                missing_fields = [field for field in required_fields if pd.isna(row[field])]
                logging.debug(f"Row {idx} discarded. Missing fields: {', '.join(missing_fields)}")

        logging.debug(f"Valid mailing addresses: {len(valid_data)} out of {len(df)}")
        for col in NAME_COLS:
            if col in valid_data.columns:
                logging.debug(f"Valid {col} entries: {valid_data[col].notnull().sum()}")
        column_header = NAME_COLS
        file_suffix = 'address'

    elif matching_type == MatchingType.COMBINED:
        logging.debug("Processing combined matching...")
        required_fields = ['first name', 'last name', 'country', 'zip']
        optional_fields = [col for col in [EMAIL_COL, PHONE_COL, ALT_PHONE_COL] if col in df.columns]
        combined_fields = required_fields + optional_fields

        # First, filter for rows that have all required fields
        valid_data = df[combined_fields].dropna(subset=required_fields)

        # Then, keep rows that have at least one non-empty optional field (email or phone)
        valid_data = valid_data[valid_data[optional_fields].notnull().any(axis=1)]

        # Create separate rows for alternate phone numbers
        if ALT_PHONE_COL in valid_data.columns:
            alt_phone_data = valid_data[valid_data[ALT_PHONE_COL].notnull()].copy()
            alt_phone_data[PHONE_COL] = alt_phone_data[ALT_PHONE_COL]
            alt_phone_data = alt_phone_data.drop(columns=[ALT_PHONE_COL])
            valid_data = valid_data.drop(columns=[ALT_PHONE_COL])
            valid_data = pd.concat([valid_data, alt_phone_data], ignore_index=True)

        logging.debug(f"Valid combined entries: {len(valid_data)} out of {len(df)}")
        for col in combined_fields:
            if col in valid_data.columns:
                logging.debug(f"Valid {col} entries: {valid_data[col].notnull().sum()}")
        column_header = [col for col in combined_fields if col != ALT_PHONE_COL]
        file_suffix = 'combined'

    else:
        logging.warning(f"Unsupported matching type: {matching_type}")
        return pd.DataFrame(), [], len(df), {}

    if valid_data.empty:
        logging.warning(f"No valid data found for {matching_type}")
        return pd.DataFrame(), [], len(df), validation_stats

    # Apply consent filter if required
    if filter_by_consent and CONSENT_COL in df.columns:
        before_consent_filter = len(valid_data)
        valid_data = valid_data[valid_data.index.isin(df[df[CONSENT_COL].isin(['true', 'yes', '1', True, 1])].index)]
        after_consent_filter = len(valid_data)
        logging.debug(f"Applied consent filter: {after_consent_filter} rows remaining out of {before_consent_filter}")

    output_files = []

    # Apply hashing if enabled
    if hash_enabled:
        for col in column_header:
            if col in valid_data.columns:
                valid_data[col] = valid_data[col].apply(hash_data)
        logging.debug("Applied hashing to output data")

    # Save global file
    global_file_name = directory_path / f"{base_file_name}-{file_suffix}.csv"
    global_file_name = handle_existing_file(global_file_name, overwrite)
    valid_data.to_csv(global_file_name, index=False)
    output_files.append((str(global_file_name), len(valid_data)))
    logging.debug(f"Saved global file: {global_file_name} with {len(valid_data)} rows")

    # Generate yearly files if Date column exists in the original DataFrame
    if date_col in df.columns:
        df[YEAR_COL] = df[date_col].apply(extract_year)
        years = sorted(df[YEAR_COL].dropna().unique())
        for year in years:
            year_mask = df[YEAR_COL] == year
            yearly_data = valid_data[valid_data.index.isin(df[year_mask].index)].copy()
            if not yearly_data.empty:
                yearly_file_name = directory_path / f"{base_file_name}-{file_suffix}-{int(year)}.csv"
                yearly_file_name = handle_existing_file(yearly_file_name, overwrite)
                yearly_data.to_csv(yearly_file_name, index=False)
                output_files.append((str(yearly_file_name), len(yearly_data)))
                logging.debug(f"Saved yearly file for {year}: {yearly_file_name} with {len(yearly_data)} rows")

    logging.debug(f"Finished processing {matching_type}. Total output files: {len(output_files)}")

    return valid_data, output_files, len(df), validation_stats


def read_excel_file(file_path: Path) -> pd.DataFrame:
    workbook = openpyxl.load_workbook(file_path, data_only=True)
    sheet = workbook.active
    headers = [cell.value.lower() if cell.value else None for cell in sheet[1]]

    data = [{header: (cell_value.lstrip("'") if isinstance(cell_value, str) else cell_value)
             for header, cell_value in zip(headers, row)}
            for row in sheet.iter_rows(min_row=2, values_only=True)]

    return pd.DataFrame(data)

COUNTRY_DICT = create_country_dict()

def main(file_paths: List[str], overwrite: bool, hash_enabled: bool, log_level: str) -> None:
    setup_logging(log_level)

    if not file_paths:
        logging.error("No input files provided. Please specify at least one CSV or Excel file.")
        return

    all_validation_stats = {}

    for file_path in file_paths:
        file_path = Path(file_path)
        if not file_path.is_file():
            logging.error(f"File not found: {file_path}")
            continue

        logging.info(f"Processing file: {file_path}")

        # Read the input file
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, dtype=str)
                df.columns = df.columns.str.lower()
            elif file_path.suffix.lower() in ('.xlsx', '.xls'):
                df = read_excel_file(file_path)
            else:
                logging.error(f"Unsupported file format for {file_path}. Please provide a .csv or .xlsx file.")
                continue
        except Exception as e:
            logging.error(f"An error occurred while processing {file_path}: {e}")
            continue

        # Retain only the specified columns
        existing_columns = [col for col in EXPECTED_COLUMNS if col in df.columns]
        df = df[existing_columns].copy()

        # Display column information
        show_column_info(df)

        # Check for the presence of the Consent column
        consent_present = CONSENT_COL in df.columns
        filter_by_consent = False

        if consent_present:
            consent_choice = input("Do you want to export all valid records, or only those where consent is granted? (all/consent): ").strip().lower()
            filter_by_consent = consent_choice == 'consent'

        keep_unvalidated_phones = input("Do you want to keep phone numbers that appear correctly formatted but are not validated? (y/n): ").strip().lower() == 'y'

        # Extract Year if Date column exists
        if DATE_COL in df.columns:
            df[YEAR_COL] = df[DATE_COL].apply(extract_year)

        # Display available matching options
        options = []
        if is_valid_column(df, [EMAIL_COL]):
            email_valid_count = df[EMAIL_COL].notnull().sum()
            email_valid_percentage = (email_valid_count / len(df)) * 100
            options.append((1, f"Email Address Matching: {email_valid_count} rows ({email_valid_percentage:.2f}% valid records)", MatchingType.EMAIL))

        phone_columns = [col for col in [PHONE_COL, ALT_PHONE_COL] if col in df.columns]
        if phone_columns:
            phone_valid_count = df[phone_columns].notnull().any(axis=1).sum()
            phone_valid_percentage = (phone_valid_count / len(df)) * 100
            options.append((2, f"Phone Matching: {phone_valid_count} rows ({phone_valid_percentage:.2f}% valid records)", MatchingType.PHONE))

        if is_valid_column(df, NAME_COLS):
            mailing_valid_count = df[NAME_COLS].notnull().all(axis=1).sum()
            mailing_valid_percentage = (mailing_valid_count / len(df)) * 100
            options.append((3, f"Mailing Address Matching: {mailing_valid_count} rows ({mailing_valid_percentage:.2f}% valid records)", MatchingType.MAILING_ADDRESS))

        combined_columns = NAME_COLS + [col for col in [EMAIL_COL, PHONE_COL, ALT_PHONE_COL] if col in df.columns]
        if is_valid_column(df, NAME_COLS) and (is_valid_column(df, [EMAIL_COL]) or is_valid_column(df, [PHONE_COL]) or is_valid_column(df, [ALT_PHONE_COL])):
            combined_valid_count = df[NAME_COLS].notnull().all(axis=1) & df[[col for col in [EMAIL_COL, PHONE_COL, ALT_PHONE_COL] if col in df.columns]].notnull().any(axis=1)
            combined_valid_count = combined_valid_count.sum()
            combined_valid_percentage = (combined_valid_count / len(df)) * 100
            options.append((4, f"Combined Matching: {combined_valid_count} rows ({combined_valid_percentage:.2f}% valid records)", MatchingType.COMBINED))

        # If no valid options, skip the file
        if not options:
            logging.warning(f"No valid data found for matching in {file_path}.")
            continue

        # Base filename for outputs
        base_file_name = file_path.stem.lower().replace(" ", "-")

        # Display options to the user
        print("\nMatching options found:\n")
        for opt in options:
            print(f"  {opt[0]}. {opt[1]}")
        print()  # Blank line after the numbered list

        choice_input = input(f"Please choose which matching option(s) to output ({', '.join(map(str, [opt[0] for opt in options]))} or 'all'): ").strip()

        # Parse user input for options
        if choice_input.lower() == "all":
            selected_options = [opt[0] for opt in options]
        else:
            try:
                selected_options = [int(ch.strip()) for ch in choice_input.split(',')]
            except ValueError:
                logging.error("Invalid input format. Please enter numbers separated by commas only.")
                continue

            # Validate selected options
            invalid_selections = [opt for opt in selected_options if opt not in [option[0] for option in options]]
            if invalid_selections:
                logging.error(f"Invalid selection(s): {', '.join(map(str, invalid_selections))}. Please enter valid option numbers separated by commas.")
                continue

        file_validation_stats = {}

        # Process each selected option
        for choice in selected_options:
            selected_option = next((opt for opt in options if opt[0] == choice), None)
            if selected_option:
                matching_type = selected_option[2]
                directory_name = matching_type.name.lower().replace('_', '-')

                valid_df, output_files, total_input_rows, validation_stats = process_and_save(
                    df,
                    EMAIL_COL,
                    PHONE_COL,
                    ALT_PHONE_COL,
                    base_file_name,
                    directory_name,
                    date_col=DATE_COL if DATE_COL in df.columns else None,
                    filter_by_consent=filter_by_consent,
                    hash_enabled=hash_enabled,
                    overwrite=overwrite,
                    matching_type=matching_type,
                    keep_unvalidated_phones=keep_unvalidated_phones
                )

                if valid_df.empty:
                    logging.warning(f"No valid data returned for matching type '{matching_type}'.")
                else:
                    print(f"\nOutput files for {matching_type.name}:")
                    for file_name, row_count in output_files:
                        percentage = (row_count / total_input_rows) * 100
                        print(f"  • {file_name}: {row_count} rows ({percentage:.2f}% of input)")

                    # Accumulate validation stats for this file
                    for col, stats in validation_stats.items():
                        if col not in file_validation_stats:
                            file_validation_stats[col] = stats
                        else:
                            file_validation_stats[col] = tuple(sum(x) for x in zip(file_validation_stats[col], stats))

        all_validation_stats[file_path.name] = file_validation_stats

    # Print validation statistics for all files at the end
    print("\nValidation statistics for all input files:")
    for file_name, stats in all_validation_stats.items():
        print(f"\n{file_name}:")
        for col, (valid_count, unvalidated_count, original_count) in stats.items():
            valid_percentage = (valid_count / original_count) * 100 if original_count > 0 else 0
            unvalidated_percentage = (unvalidated_count / original_count) * 100 if original_count > 0 else 0
            total_kept = valid_count + unvalidated_count
            total_percentage = (total_kept / original_count) * 100 if original_count > 0 else 0
            print(f"  • {col}:")
            print(f"    - {valid_count} validated out of {original_count} ({valid_percentage:.2f}% validated)")
            if unvalidated_count > 0:
                print(f"    - {unvalidated_count} unvalidated but kept ({unvalidated_percentage:.2f}% unvalidated)")
            print(f"    - Total kept: {total_kept} ({total_percentage:.2f}% of original)")

    if log_level.upper() == 'DEBUG':
        print_debug_summary()

def run():
    parser = argparse.ArgumentParser(description="Process subscriber data and perform various matching operations.")
    parser.add_argument('files', metavar='FILE', nargs='*', help='Input CSV or Excel files to process.')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing output files without prompting.')
    parser.add_argument('--hash', action='store_true', help='Hash the values in the output files.')
    parser.add_argument('--log-level', default='ERROR', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the logging level (default: ERROR).')
    args = parser.parse_args()

    if not args.files:
        parser.print_help()
        print("\nField requirements for each matching type:\n")
        print("  Email matching:")
        print(f"    - {EMAIL_COL}\n")
        print("  Phone matching:")
        print(f"    - {PHONE_COL}")
        print(f"    - {ALT_PHONE_COL} (optional)\n")
        print("  Address matching:")
        print("    - " + "\n    - ".join(NAME_COLS) + "\n")
        print("  Combined matching:")
        print("    - " + "\n    - ".join(NAME_COLS))
        print(f"    - At least one of: {EMAIL_COL}, {PHONE_COL}, or {ALT_PHONE_COL}\n")
        print("  Optional fields for all matching types:")
        print(f"    - {DATE_COL}")
        print(f"    - {CONSENT_COL}")
        return

    main(args.files, args.overwrite, args.hash, args.log_level)

if __name__ == "__main__":
    run()
