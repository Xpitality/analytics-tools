# Analytics tools by Xpitality
This is a collection of tools to automate operations with Google Analytics 4 and Google Ads

# GA4 Audience Transfer Script

This script allows you to migrate audiences from one Google Analytics 4 (GA4) property to another. It can also import audiences from a file into a GA4 property and export audiences from a GA4 property to a file.

## Prerequisites

1. **Python 3.7 or higher**: Ensure you have Python installed on your machine.
2. **Google Cloud Project**: You need to have a Google Cloud project with the Google Analytics API enabled.

## Setting Up on Google Cloud

### Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project by clicking on the project dropdown and selecting "New Project".
3. Name your project and click "Create".

### Step 2: Enable the Google Analytics API

1. In the Google Cloud Console, navigate to the **API & Services** > **Library**.
2. Search for "Google Analytics Admin API" and click on it.
3. Click on the **Enable** button.

### Step 3: Set Up OAuth 2.0 Credentials

1. Go to **API & Services** > **Credentials**.
2. Click on **Create Credentials** and select **OAuth client ID**.
3. If prompted, configure the consent screen by providing the required information.
4. Select **Desktop app** as the application type and click **Create**.
5. Once created, click on the download icon to download the `credentials.json` file. This file will be used for authentication.

### Step 4: Share Access with the Service Account (if needed)

If you are using a service account, ensure that the service account has the necessary permissions on the GA4 property. You can do this by:

1. Go to your GA4 property in [Google Analytics](https://analytics.google.com/).
2. Navigate to **Admin** > **Account Access Management** or **Property Access Management**.
3. Click on the "+" icon to add the service account email and assign the necessary roles.

## Setting Up Locally

### Step 1: Install Python and Virtual Environment

Ensure you have Python 3.7 or higher installed. You can check your Python version by running:

```bash
python --version
```

If Python is not installed, download and install it from [python.org](https://www.python.org/downloads/).

### Step 2: Create a Virtual Environment

1. Open a terminal and navigate to the directory where you want to set up the project.
2. Create a virtual environment using the following command:

   ```bash
   python -m venv ga4-audience-env
   ```

3. Activate the virtual environment:

   - On Windows:
     ```bash
     ga4-audience-env\Scripts\activate
     ```

   - On macOS/Linux:
     ```bash
     source ga4-audience-env/bin/activate
     ```

### Step 3: Install Required Python Packages

With the virtual environment activated, install the required packages using pip:

```bash
pip install --upgrade google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

### Step 4: Download the Script

Download the `ga4_audience_transfer.py` script and save it in your project directory.

### Step 5: Prepare Configuration

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

   ### Configuration Keys

**`client_secrets_file`**:
   - **Description**: This is the path to the `credentials.json` file that you downloaded from Google Cloud after creating your OAuth 2.0 credentials.
   - **Example**: `"client_secrets_file": "credentials.json"`

**`token_file`**:
   - **Description**: This is the path to the file where the OAuth 2.0 access token will be stored after your first login. The script will create this file automatically if it does not exist.
   - **Example**: `"token_file": "token.json"`

**`scopes`**:
   - **Description**: This is an array that specifies the permissions that the script will request from Google Analytics. The script needs permission to edit analytics data.
   - **Example**: `"scopes": ["https://www.googleapis.com/auth/analytics.edit"]`

**`source_property_id`**:
   - **Description**: This is the Google Analytics 4 property ID from which you want to migrate audiences. You can find this ID in your Google Analytics account.
   - **Example**: `"source_property_id": "123456789"`

**`target_property_id`**:
   - **Description**: This is the Google Analytics 4 property ID to which you want to migrate audiences. Like the source property ID, you can find this ID in your Google Analytics account.
   - **Example**: `"target_property_id": "987654321"`

## How to Use the Script

### Option 1: Export Audiences from Source Property

To export audiences from a source property to a file, run the following command:

```bash
python ga4_audience_transfer.py export --file audiences.json
```

### Option 2: Import Audiences into Target Property

To import audiences from a file into a target property, run the following command:

```bash
python ga4_audience_transfer.py import --file audiences.json
```

### Option 3: Migrate Audiences between Properties

To migrate audiences from a source property to a target property, run the following command:

```bash
python ga4_audience_transfer.py migrate
```

### Additional Notes

- Ensure you have the necessary permissions on both the source and target GA4 properties.
- The script will provide output indicating the success or failure of each operation, including handling errors such as reaching the maximum number of audiences allowed.
