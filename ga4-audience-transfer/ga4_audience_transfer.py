import json
import os
import argparse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from datetime import datetime

def authenticate(config):
    """Authenticate with Google API and return a service object."""
    creds = None
    if os.path.exists(config['token_file']):
        creds = Credentials.from_authorized_user_file(config['token_file'], config['scopes'])
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config['client_secrets_file'], config['scopes'])
            creds = flow.run_local_server(port=0)
        with open(config['token_file'], 'w') as token:
            token.write(creds.to_json())
    return build('analyticsadmin', 'v1alpha', credentials=creds)

def get_audiences(service, property_id):
    """Retrieve all audiences from the specified property."""
    audiences = []
    request = service.properties().audiences().list(parent=f'properties/{property_id}')
    
    while request is not None:
        response = request.execute()
        audiences.extend(response.get('audiences', []))
        request = service.properties().audiences().list_next(previous_request=request, previous_response=response)  # Handle pagination

    return audiences

def create_audience(service, property_id, audience):
    """Create an audience in the target property."""
    # Ensure 'filterClauses' is provided
    if 'filterClauses' not in audience or not audience['filterClauses']:
        print(f"Audience '{audience['displayName']}' has no filter clauses. Defaulting to an empty filter clause.")
        audience['filterClauses'] = [{'filterType': 'filterTypeUnspecified', 'fieldName': 'fieldNameUnspecified', 'stringFilter': {'matchType': 'matchTypeUnspecified', 'value': ''}}]

    # Remove the 'name' field if it exists
    audience.pop('name', None)

    print(f"Creating audience: {audience['displayName']}")
    
    try:
        request = service.properties().audiences().create(
            parent=f'properties/{property_id}',
            body=audience
        )
        response = request.execute()
        print(f"Successfully created audience: {response['displayName']}")
    except HttpError as e:
        if e.resp.status == 429:
            print("Error: Maximum audience limit reached. Unable to create more audiences.")
            raise  # Raise the error to stop execution
        else:
            print(f"Failed to create audience '{audience['displayName']}': {e}")

def import_audiences(service, target_property_id, file_path):
    """Import audiences from the given file to the target account."""
    with open(file_path, 'r') as file:
        audiences = json.load(file)

    # Retrieve existing audiences in the target property
    target_audiences = get_audiences(service, target_property_id)
    target_audience_names = {a['displayName'].strip() for a in target_audiences}  # Normalize names

    stats = {'migrated': 0, 'skipped': 0}
    for audience in audiences:
        audience_name = audience['displayName'].strip()  # Use .strip() for comparison
        # Normalize for comparison
        if audience_name in target_audience_names:
            print(f"Skipping existing audience: {audience_name}")
            stats['skipped'] += 1
            continue

        try:
            create_audience(service, target_property_id, audience)
            stats['migrated'] += 1
        except HttpError as e:
            print(f"Failed to create audience: {e}")

    stats['total_destination'] = len(get_audiences(service, target_property_id))
    print_summary('import', stats)

def migrate_audiences(service, source_property_id, target_property_id):
    """Migrate audiences from source property to target property."""
    source_audiences = get_audiences(service, source_property_id)
    target_audiences = get_audiences(service, target_property_id)
    target_audience_names = {a['displayName'].strip() for a in target_audiences}

    stats = {'migrated': 0, 'skipped': 0, 'source_count': len(source_audiences)}  # Track source count
    for audience in source_audiences:
        original_display_name = audience['displayName'].strip()
        
        # Check if the audience already exists in the target property
        if original_display_name in target_audience_names:
            # Create a new audience with a modified name
            audience['displayName'] = f"{original_display_name} - IMPORTED {int(datetime.now().timestamp())}"
            print(f"Audience already exists, creating new: {audience['displayName']}")
        else:
            audience['displayName'] = original_display_name
        
        try:
            create_audience(service, target_property_id, audience)
            stats['migrated'] += 1
        except HttpError as e:
            if e.resp.status == 429:
                print("Error: Maximum audience limit reached. Unable to create more audiences.")
                raise  # Stop execution if the limit is reached
            else:
                print(f"Failed to create audience: {e}")

    stats['total_destination'] = len(get_audiences(service, target_property_id))
    print_summary('migrate', stats)

def export_audiences(service, source_property_id, file_path):
    """Export audiences from source property to a file."""
    source_audiences = get_audiences(service, source_property_id)
    with open(file_path, 'w') as file:
        json.dump(source_audiences, file, indent=4)

    stats = {'source_count': len(source_audiences), 'exported': len(source_audiences)}
    print_summary('export', stats)

def print_summary(mode, stats):
    """Print a summary of the operation."""
    if mode == 'migrate':
        print(f"Migrate summary:")
        print(f" - Audiences in source account: {stats['source_count']}")
        print(f" - Audiences migrated: {stats['migrated']}")
        print(f" - Audiences skipped: {stats['skipped']}")
        print(f" - Total audiences in destination account: {stats['total_destination']}")
    elif mode == 'export':
        print(f"Export summary:")
        print(f" - Audiences in source account: {stats['source_count']}")
        print(f" - Audiences exported: {stats['exported']}")
    elif mode == 'import':
        print(f"Import summary:")
        print(f" - Audiences migrated: {stats['migrated']}")
        print(f" - Audiences skipped: {stats['skipped']}")
        print(f" - Total audiences in destination account: {stats['total_destination']}")

def main():
    with open('config.json') as f:
        config = json.load(f)

    service = authenticate(config)

    parser = argparse.ArgumentParser(description='Manage GA4 audiences.')
    parser.add_argument('mode', choices=['migrate', 'export', 'import'], help='Mode of operation')
    parser.add_argument('--file', help='File path for exporting or importing')
    args = parser.parse_args()

    if args.mode == 'migrate':
        if not config.get('source_property_id') or not config.get('target_property_id'):
            print("Error: Source and target property IDs are required for migration.")
            return
        try:
            migrate_audiences(service, config['source_property_id'], config['target_property_id'])
        except HttpError as e:
            print(f"Migration failed: {e}")
    elif args.mode == 'export':
        if not config.get('source_property_id') or not args.file:
            print("Error: Source property ID and file path are required for exporting.")
            return
        export_audiences(service, config['source_property_id'], args.file)
    elif args.mode == 'import':
        if not config.get('target_property_id') or not args.file:
            print("Error: Target property ID and file path are required for importing.")
            return
        import_audiences(service, config['target_property_id'], args.file)

if __name__ == '__main__':
    main()

