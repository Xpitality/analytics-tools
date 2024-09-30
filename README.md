
# Analytics Tools by Xpitality

This repository contains two (so far) tools to automate operations with Google Analytics 4 and Google Ads:

1. **GA4 Audience Transfer (GAT) Script**
2. **Customer Match Importer (CMI) Script**

## System Requirements

- Designed and tested for Mac and Linux systems.
- Python 3.7 or higher.

## Installation and Setup

1. Clone this repository:
```bash
git clone https://github.com/Xpitality/analytics-tools.git
cd analytics-tools
```

2. Set up the virtual environments:
```bash
chmod +x setup_venv.sh
./setup_venv.sh
```

   This script will:
   - Create two new virtual environments (`ga4-audience-env` for the GAT script and `cmi-env` for the CMI script).
   - Install required packages from `requirements.txt` for each environment.

3. Activate the appropriate virtual environment:

   For GA4 Audience Transfer Script:
```bash
cd ga4_audience_transfer
./activate_venv.sh
```

   For Customer Match Importer Script:
```bash
cd customer_match_importer
./activate_venv.sh
```

   **Note:** Always activate the appropriate virtual environment before running either script.

4. When you're done, deactivate the virtual environment:
```bash
deactivate
```

## GA4 Audience Transfer (GAT) Script

This script allows you to migrate audiences from one Google Analytics 4 (GA4) property to another. It can also import audiences from a file into a GA4 property and export audiences from a GA4 property to a file.

### Prerequisites

1. **Python 3.7 or higher:** Ensure you have Python installed on your machine.
2. **Google Cloud Project:** You need to have a Google Cloud project with the Google Analytics API enabled.

### Setting Up on Google Cloud

#### Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project by clicking on the project dropdown and selecting "New Project".
3. Name your project and click "Create".

#### Step 2: Enable the Google Analytics API

1. In the Google Cloud Console, navigate to **API & Services** \> **Library**.
2. Search for "Google Analytics Admin API" and click on it.
3. Click on the **Enable** button.

#### Step 3: Set Up OAuth 2.0 Credentials

1. Go to **API & Services** \> **Credentials**.
2. Click on **Create Credentials** and select **OAuth client ID**.
3. If prompted, configure the consent screen by providing the required information.
4. Select **Desktop app** as the application type and click **Create**.
5. Once created, click on the download icon to download the `credentials.json` file. This file will be used for authentication.

#### Step 4: Share Access with the Service Account (if needed)

If you are using a service account, ensure that the service account has the necessary permissions on the GA4 property. You can do this by:

1. Go to your GA4 property in [Google Analytics](https://analytics.google.com/).
2. Navigate to **Admin** \> **Account Access Management** or **Property Access Management**.
3. Click on the "+" icon to add the service account email and assign the necessary roles.

### Configuration

Create a `config.json` file in the same directory as the script with the following structure:

```json
{
  "client_secrets_file": "credentials.json",
  "token_file": "token.json",
  "scopes": ["https://www.googleapis.com/auth/analytics.edit"],
  "source_property_id": "YOUR_SOURCE_PROPERTY_ID",
  "target_property_id": "YOUR_TARGET_PROPERTY_ID"
}
```

Replace `YOUR_SOURCE_PROPERTY_ID` and `YOUR_TARGET_PROPERTY_ID` with the actual property IDs from Google Analytics.

#### Configuration Keys

- **`client_secrets_file`**: Path to the `credentials.json` file downloaded from Google Cloud.
- **`token_file`**: Path where the OAuth 2.0 access token will be stored.
- **`scopes`**: Permissions the script will request from Google Analytics.
- **`source_property_id`**: GA4 property ID from which you want to migrate audiences.
- **`target_property_id`**: GA4 property ID to which you want to migrate audiences.

### Usage

1. Export audiences from the source property:
```bash
python gat.py export --file audiences.json
```

2. Import audiences into the target property:
```bash
python gat.py import --file audiences.json
```

3. Migrate audiences between properties:
```bash
python gat.py migrate
```

### Additional Notes

- Ensure you have the necessary permissions on both the source and target GA4 properties.
- The script will provide output indicating the success or failure of each operation, including handling errors such as reaching the maximum number of audiences allowed.

## Customer Match Importer (CMI) Script

### Overview

The Customer Match Importer (CMI) is designed to process, validate, and prepare customer data for use with Google Ads' Customer Match feature. It supports various matching types, performs data validation, and can generate hashed output suitable for upload to Google Ads.

### Features

- Multiple matching types: Email, Phone, Mailing Address, and Combined.
- Data validation for emails, phone numbers, names, and countries.
- Option to keep unvalidated but correctly formatted phone numbers.
- Consent filtering.
- Data hashing for privacy.
- Yearly file generation based on date information.
- Detailed logging and debug information.
- Support for CSV and Excel input files.

### Usage

Run the script using the following command:

```bash
python3 cmi.py [OPTIONS] [FILE ...]
```

#### Positional Arguments

- `FILE`: Input CSV or Excel files to process.

#### Options

- `--overwrite`: Overwrite existing output files without prompting.
- `--hash`: Hash the values in the output files.
- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Set the logging level (default: ERROR).

### Field Requirements for Each Matching Type

#### Email Matching:
- `email`

#### Phone Matching:
- `phone`
- `alternate phone` (optional)

#### Address Matching:
- `first name`
- `last name`
- `country`
- `zip`

#### Combined Matching:
- `first name`
- `last name`
- `country`
- `zip`
- At least one of: `email`, `phone`, or `alternate phone`

#### Optional Fields for All Matching Types:
- `date`
- `consent`

### Example Commands

1. **Process a CSV file, overwrite existing output, hash values, and set logging to INFO:**
```bash
python3 cmi.py --overwrite --hash --log-level INFO customers.csv
```

2. **Process a CSV file without hashing and overwrite existing files:**
```bash
python3 cmi.py --overwrite customers.csv
```

3. **Process multiple files and log warnings only:**
```bash
python3 cmi.py --log-level WARNING customers1.csv customers2.xlsx
```

4. **Process with default logging (ERROR) and without overwriting existing files:**
```bash
python3 cmi.py customers.csv
```

## Data Privacy and Security

These scripts handle potentially sensitive user data. Ensure you comply with all relevant data protection regulations (such as GDPR) when using these tools. Do not share your configuration files or any output containing user data.

## Troubleshooting

- If you're having issues with package installation, try upgrading pip:
```bash
pip install --upgrade pip
```

- Ensure you have the correct Python version installed:
```bash
python --version
```
   These scripts require Python 3.7 or higher.

- For any other issues, please check the [issues page](https://github.com/Xpitality/analytics-tools/issues) or open a new issue if your problem isn't addressed.

## Contributing

Contributions to improve these tools are welcome. Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0) - see the [LICENSE](LICENSE) file in the root of the project for details.

## Disclaimer

These tools are provided under the terms of the GPL-3.0 license, **WITHOUT ANY WARRANTY**; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

Always test thoroughly before using in a production environment and ensure compliance with relevant data protection regulations and platform policies.

## Contact

For any questions or concerns, please open an issue on the GitHub repository.
