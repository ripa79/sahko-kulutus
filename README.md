# sahko-kulutus

# Usage

create a .env file with the following variables:

```
ELINIA_USERNAME=<your username>
ELINIA_PASSWORD=<your password>
SPOT_MARGIN=<your spot margin>
```

Create a virtual environment and install the dependencies:

```
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

Run with following commands:

```
python 1_elenia_consumption_data_json.py
python 2_vattenfall_price_data.py
python 3_combine.py
python 4_data_analysis.py
```

