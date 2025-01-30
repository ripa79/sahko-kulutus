# sahko-kulutus

## Setup

1. Create a .env file with the following variables:

```
ELINIA_USERNAME=<your username>
ELINIA_PASSWORD=<your password>
SPOT_MARGIN=<your spot margin>
```

2. Create a virtual environment and install the dependencies:

### Windows

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### macOS/Linux

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Run the PowerShell script to execute all the steps:

```
.\run_all.ps1
```

Alternatively, you can run the scripts individually:

```
python 1_elenia_consumption_data_json.py
python 2_vattenfall_price_data.py
python 3_combine.py
python 4_data_analysis.py
```

