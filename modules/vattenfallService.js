const axios = require('axios');
const fs = require('fs').promises;
const path = require('path');
const dotenv = require('dotenv');

dotenv.config();

class VattenfallService {
    constructor() {
        this.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36'
        };
    }

    async fetchPriceData() {
        const year = process.env.YEAR;
        const startDate = `${year}-01-01`;
        const endDate = `${year}-12-31`;
        const url = `https://www.vattenfall.fi/api/price/spot/${startDate}/${endDate}?lang=fi`;

        try {
            const response = await axios.get(url, { headers: this.headers });
            const data = response.data;

            // Add VAT (25.5%) to the values
            const VAT_RATE = 0.255;
            const processedData = data.map(row => ({
                ...row,
                value: Number((row.value * (1 + VAT_RATE)).toFixed(2))
            }));

            // Ensure downloads directory exists
            const downloadsDir = path.join(process.cwd(), 'downloads');
            await fs.mkdir(downloadsDir, { recursive: true });

            // Save to CSV
            const csvContent = this.convertToCSV(processedData);
            const csvFilename = path.join(downloadsDir, `vattenfall_hinnat_${year}.csv`);
            await fs.writeFile(csvFilename, csvContent);

            console.log(`Successfully fetched and saved Vattenfall price data for ${year}`);
            return processedData;
        } catch (error) {
            console.error('Failed to fetch Vattenfall price data:', error.message);
            throw error;
        }
    }

    convertToCSV(data) {
        if (!data || data.length === 0) return '';
        
        // Only use timestamp and value fields
        const csvRows = [
            'timeStamp;value',
            ...data.map(row => `${row.timeStamp};${row.value}`)
        ];
        
        return csvRows.join('\n');
    }
}

module.exports = new VattenfallService();