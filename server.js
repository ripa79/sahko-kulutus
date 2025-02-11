const express = require('express');
const cron = require('node-cron');
const cors = require('cors');
const path = require('path');
const fs = require('fs').promises;
require('dotenv').config();

const eleniaService = require('./modules/eleniaService');
const vattenfallService = require('./modules/vattenfallService');
const dataProcessor = require('./modules/dataProcessor');

// Replace console.log with timestamped version
const log = (...args) => {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}]`, ...args);
};

// Replace console.error with timestamped version
const logError = (...args) => {
    const timestamp = new Date().toISOString();
    console.error(`[${timestamp}]`, ...args);
};

// Initialize application
const app = express();
log('Initializing Express application...');

// Request logging middleware with more details
app.use((req, res, next) => {
    log(`${req.method} ${req.url} - Headers:`, req.headers);
    next();
});

// Middleware setup
app.use(cors());
app.use(express.json());

// Move static files middleware BEFORE API routes
const staticPath = path.join(__dirname, 'public');
app.use(express.static(staticPath));
log(`Static files being served from: ${staticPath}`);

// API endpoint to get analysis data
app.get('/api/analysis', async (req, res) => {
    log('Received request for analysis data');
    try {
        const filePath = path.join(__dirname, 'processed', 'combined_data.csv');
        log(`Attempting to read file: ${filePath}`);
        
        const exists = await fs.access(filePath).then(() => true).catch(() => false);
        log(`Combined data file exists: ${exists}`);
        
        if (!exists) {
            log('Combined data file not found, triggering data update...');
            await updateData();
        }
        
        const data = await fs.readFile(filePath, 'utf-8');
        log('Successfully read combined data file');
        res.json({ data });
    } catch (error) {
        logError('Error reading analysis data:', error);
        res.status(500).json({ error: 'Failed to retrieve analysis data', details: error.message });
    }
});

// API endpoint to manually trigger data update
app.post('/api/update', async (req, res) => {
    log('Received manual update request');
    try {
        await updateData();
        res.json({ message: 'Data update completed successfully' });
    } catch (error) {
        logError('Error updating data:', error);
        res.status(500).json({ error: 'Failed to update data', details: error.message });
    }
});

// Move catch-all route to be last and update path handling
app.get(['/', '/overview', '/consumption', '/prices', '/patterns'], (req, res) => {
    const page = req.path === '/' ? 'index.html' : `${req.path.slice(1)}.html`;
    res.sendFile(path.join(staticPath, page));
});

// Function to update all data
async function updateData() {
    log('Starting data update process...');
    try {
        // Step 1: Fetch Elenia consumption data
        log('Fetching Elenia consumption data...');
        await eleniaService.fetchConsumptionData();

        // Step 2: Fetch Vattenfall price data
        log('Fetching Vattenfall price data...');
        await vattenfallService.fetchPriceData();

        // Step 3: Combine data
        log('Combining data...');
        await dataProcessor.combineData();

        log('Data update completed successfully');
        return true;
    } catch (error) {
        logError('Error in data update process:', error);
        throw error;
    }
}

// Schedule daily data fetch using environment variable
const updateHour = process.env.UPDATE_HOUR || '2'; // Default to 2 AM if not set
log(`Setting up daily cron job for ${updateHour}:00...`);
cron.schedule(`0 ${updateHour} * * *`, async () => {
    log('Running daily data update...');
    try {
        await updateData();
        log('Daily data update completed successfully');
    } catch (error) {
        logError('Error in daily data update:', error);
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    logError('Unhandled error:', err);
    logError('Error details:', {
        message: err.message,
        stack: err.stack,
        type: err.constructor.name
    });
    res.status(500).json({ error: 'Internal server error', details: err.message });
});

// Start server first, before any initialization
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    log(`Server running on port ${PORT}`);
    log(`Static files being served from: ${staticPath}`);
});

// Initialize directories after server is running
(async () => {
    try {
        // Create directories non-blocking
        for (const dir of ['processed', 'downloads', 'public']) {
            fs.mkdir(path.join(__dirname, dir), { recursive: true })
                .catch(err => logError(`Error creating ${dir} directory:`, err));
        }
        
        // Check for existing data
        const dataFile = path.join(__dirname, 'processed', 'combined_data.csv');
        const exists = await fs.access(dataFile).then(() => true).catch(() => false);
        
        if (!exists) {
            log('No existing data found. Starting background update...');
            updateData().catch(err => logError('Initial data update failed:', err));
        }
    } catch (error) {
        logError('Initialization error:', error);
    }
})();