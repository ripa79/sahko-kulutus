#!/bin/bash

# Activate virtual environment
source ./venv/bin/activate

# Run scripts in sequence
run_script() {
    echo "Running $1..."
    python "$1"
}

try_run_scripts() {
    run_script "1_elenia_consumption_data.py"
    run_script "2_vattenfall_price_data.py"
    run_script "3_combine.py"
    run_script "4_data_analysis.py"
    echo "All scripts completed successfully!"
}

# Execute scripts and handle errors
if try_run_scripts; then
    :
else
    echo "An error occurred!"
fi

# Deactivate virtual environment
deactivate
