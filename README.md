# sahko-kulutus

## Setup

You can use either Python or Node.js to run this project.

### Python Setup

1. Create a .env file with the following variables:

```
ELENIA_USERNAME=<your username>
ELENIA_PASSWORD=<your password>
SPOT_MARGIN=0.6
YEAR="2025"
```

2. Create a virtual environment and install the dependencies:

#### Windows

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### macOS/Linux

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Run the shell script to execute all the steps:

```
./run_analysis.sh  # Linux/macOS
run_analysis.ps1   # Windows
```

Alternatively, you can run the scripts individually:

```
python 1_elenia_consumption_data.py
python 2_vattenfall_price_data.py
python 3_combine.py
python 4_data_analysis.py
```

### Node.js Setup

1. Use the same .env file as above

2. Install dependencies:
```
npm install
```

3. Start the server:
```
npm start
```

For development with auto-reload:
```
npm run dev
```

The server runs on port 3000 by default and provides:

#### Web Interface
- Overview: http://localhost:3000/overview.html
- Consumption data: http://localhost:3000/consumption.html
- Price data: http://localhost:3000/prices.html
- Patterns: http://localhost:3000/patterns.html

#### API Endpoints
- GET /api/analysis - Retrieve the combined analysis data
- POST /api/update - Manually trigger data update

The server automatically updates data daily at 2 AM and creates required directories (processed, downloads, public) on startup.

