# sahko-kulutus

## Setup

You can use Node.js or Docker to run this project.

### Node.js Setup

1. Create a .env file with the following variables:

```
ELENIA_USERNAME=<your username>
ELENIA_PASSWORD=<your password>
SPOT_MARGIN=0.6
YEAR="2025"
```

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

### Docker Setup

1. Create a .env file as described in the Node.js setup section above.

2. Build and run using Docker Compose:
```
docker compose up -d
```

This will:
- Build the Node.js application container
- Start the server on port 3000
- Mount the downloads and processed directories
- Load environment variables from .env file
- Automatically restart the container unless stopped manually

To view logs:
```
docker compose logs -f
```

To stop the container:
```
docker compose down
```

