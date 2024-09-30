#!/bin/bash

# Function to create and set up a virtual environment
setup_venv() {
    local app_name=$1
    local app_dir=$2
    local venv_name="${app_name}-env"

    echo "Setting up environment for $app_name"

    # Change to the app directory
    cd "$app_dir" || exit

    # Check if the virtual environment already exists
    if [ -d "$venv_name" ]; then
        echo "Removing existing virtual environment: $venv_name"
        rm -rf "$venv_name"
    fi

    # Create a new virtual environment
    echo "Creating virtual environment: $venv_name"
    python3 -m venv "$venv_name"

    # Activate the virtual environment
    echo "Activating virtual environment: $venv_name"
    source "$venv_name/bin/activate"

    # Install required packages
    if [ -f "requirements.txt" ]; then
        echo "Installing required packages from requirements.txt"
        pip install -r requirements.txt
    else
        echo "No requirements.txt found in $app_dir. Please create one to install necessary packages."
    fi

    # Deactivate the virtual environment
    deactivate

    # Change back to the root directory
    cd - || exit

    echo "Setup complete for $app_name!"
}

# Set up virtual environment for GA4 Audience Transfer
setup_venv "ga4-audience" "ga4-audience-transfer"

# Set up virtual environment for Customer Match Importer
setup_venv "cmi" "customer-match-import"

echo "All virtual environments are set up and ready to use!"

