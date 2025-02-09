const express = require('express');
const cron = require('node-cron');
const cors = require('cors');
const path = require('path');
const fs = require('fs').promises;

const eleniaService = require('./modules/eleniaService');
const vattenfallService = require('./modules/vattenfallService');
const dataProcessor = require('./modules/dataProcessor');

// Initialize application
const app = express();
console.log('Initializing Express application...');

// Request logging middleware with more details
app.use((req, res, next) => {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.url} - Headers:`, req.headers);
    next();
});

// Middleware setup
app.use(cors());
app.use(express.json());

// Move static files middleware BEFORE API routes
const staticPath = path.join(__dirname, 'public');
app.use(express.static(staticPath));
console.log(`Static files being served from: ${staticPath}`);

// API endpoint to get analysis data
app.get('/api/analysis', async (req, res) => {
    console.log('Received request for analysis data');
    try {
        const filePath = path.join(__dirname, 'processed', 'combined_data.csv');
        console.log(`Attempting to read file: ${filePath}`);
        
        const exists = await fs.access(filePath).then(() => true).catch(() => false);
        console.log(`Combined data file exists: ${exists}`);
        
        if (!exists) {
            console.log('Combined data file not found, triggering data update...');
            await updateData();
        }
        
        const data = await fs.readFile(filePath, 'utf-8');
        console.log('Successfully read combined data file');
        res.json({ data });
    } catch (error) {
        console.error('Error reading analysis data:', error);
        res.status(500).json({ error: 'Failed to retrieve analysis data', details: error.message });
    }
});

// API endpoint to manually trigger data update
app.post('/api/update', async (req, res) => {
    console.log('Received manual update request');
    try {
        await updateData();
        res.json({ message: 'Data update completed successfully' });
    } catch (error) {
        console.error('Error updating data:', error);
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
    console.log('Starting data update process...');
    try {
        // Step 1: Fetch Elenia consumption data
        console.log('Fetching Elenia consumption data...');
        await eleniaService.fetchConsumptionData();

        // Step 2: Fetch Vattenfall price data
        console.log('Fetching Vattenfall price data...');
        await vattenfallService.fetchPriceData();

        // Step 3: Combine data
        console.log('Combining data...');
        await dataProcessor.combineData();

        console.log('Data update completed successfully');
        return true;
    } catch (error) {
        console.error('Error in data update process:', error);
        throw error;
    }
}

// Schedule daily data fetch at 2 AM
console.log('Setting up daily cron job...');
cron.schedule('0 2 * * *', async () => {
    console.log('Running daily data update...');
    try {
        await updateData();
        console.log('Daily data update completed successfully');
    } catch (error) {
        console.error('Error in daily data update:', error);
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error('Unhandled error:', err);
    console.error('Error details:', {
        message: err.message,
        stack: err.stack,
        type: err.constructor.name
    });
    res.status(500).json({ error: 'Internal server error', details: err.message });
});

// Start server first, before any initialization
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
    console.log(`Static files being served from: ${staticPath}`);
});

// Initialize directories after server is running
(async () => {
    try {
        // Create directories non-blocking
        for (const dir of ['processed', 'downloads', 'public']) {
            fs.mkdir(path.join(__dirname, dir), { recursive: true })
                .catch(err => console.error(`Error creating ${dir} directory:`, err));
        }
        
        // Check for existing data
        const dataFile = path.join(__dirname, 'processed', 'combined_data.csv');
        const exists = await fs.access(dataFile).then(() => true).catch(() => false);
        
        if (!exists) {
            console.log('No existing data found. Starting background update...');
            updateData().catch(err => console.error('Initial data update failed:', err));
        }
    } catch (error) {
        console.error('Initialization error:', error);
    }
})();