# Activate virtual environment
& "./venv/Scripts/Activate.ps1"

# Run scripts in sequence
try {
    Write-Host "Running 1_elenia_consumption_data.py..."
    python 1_elenia_consumption_data.py
    
    Write-Host "Running 2_vattenfall_price_data.py..."
    python 2_vattenfall_price_data.py
    
    Write-Host "Running 3_combine.py..."
    python 3_combine.py
    
    Write-Host "Running 4_data_analysis.py..."
    python 4_data_analysis.py
    
    Write-Host "All scripts completed successfully!"
} catch {
    Write-Host "An error occurred: $_"
} finally {
    # Deactivate virtual environment
    deactivate
}