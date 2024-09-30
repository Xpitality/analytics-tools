#!/bin/bash

# Check if the script is being sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "To activate the virtual environment, please run:"
    echo "source $0"
    echo "or"
    echo ". $0"
    exit 1
fi

# Find the virtual environment directory
venv_dir=$(find . -maxdepth 1 -type d -name "*-env" -print -quit)

if [ -z "$venv_dir" ]; then
    echo "No virtual environment directory found."
    echo "Please make sure you have created a virtual environment with a name ending in '-env'."
    return 1
fi

# Extract the environment name
env_name=$(basename "$venv_dir")

# Construct the activation script path
activate_script="$venv_dir/bin/activate"

# Check if the activation script exists
if [ ! -f "$activate_script" ]; then
    echo "Activation script not found at: $activate_script"
    echo "Please check if the virtual environment is set up correctly."
    return 1
fi

# Activate the virtual environment
source "$activate_script"

# Check if activation was successful
if [ $? -eq 0 ]; then
    echo "Virtual environment '$env_name' activated successfully."
    echo "To deactivate, simply type 'deactivate' when you're done."
else
    echo "Failed to activate the virtual environment '$env_name'."
    echo "Please check if the path '$activate_script' is correct."
fi

