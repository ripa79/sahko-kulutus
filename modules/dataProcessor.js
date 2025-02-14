const fs = require('fs').promises;
const path = require('path');
const dotenv = require('dotenv');

dotenv.config();

class DataProcessor {
    constructor() {
        this.spotMargin = parseFloat(process.env.SPOT_MARGIN);
    }

    async combineData() {
        try {
            // Read consumption data
            const consumptionFile = await fs.readFile(
                path.join(process.cwd(), 'downloads', 'consumption_data.json'),
                'utf-8'
            );
            const consumptionData = JSON.parse(consumptionFile);

            // Read price data
            const priceFile = await fs.readFile(
                path.join(process.cwd(), 'downloads', `vattenfall_hinnat_${process.env.YEAR}.csv`),
                'utf-8'
            );

            // Process price data
            const priceMap = new Map();
            const priceLines = priceFile.split('\n').slice(1); // Skip header
            priceLines.forEach(line => {
                if (line.trim()) {
                    const [timestamp, value] = line.split(';');
                    if (timestamp && value) {
                        const date = new Date(timestamp);
                        const formattedTimestamp = date.toLocaleString('sv', { 
                            timeZone: 'Europe/Helsinki',
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit'
                        }).replace(' ', 'T') + '+0200';

                        // Parse value as float and ensure it's a valid number
                        const priceValue = parseFloat(value.replace(',', '.'));
                        if (!isNaN(priceValue)) {
                            priceMap.set(formattedTimestamp, priceValue);
                        }
                    }
                }
            });

            // Debug logging
            console.log('First few price entries (after parsing):');
            let i = 0;
            for (const [key, value] of priceMap.entries()) {
                if (i++ < 5) console.log(`${key}: ${value}`);
            }

            // Process consumption data and combine with prices
            const combinedData = [];
            for (const month of consumptionData.months || []) {
                const readings = month.hourly_values_netted || month.hourly_values;
                if (readings) {
                    for (const reading of readings) {
                        const consumption = reading.v / 1000; // Convert Wh to kWh
                        const timestamp = reading.t; // Use the timestamp directly from the data

                        // Format timestamp in Helsinki timezone (+0200)
                        const date = new Date(timestamp);
                        const formattedTimestamp = date.toLocaleString('sv', { 
                            timeZone: 'Europe/Helsinki',
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit'
                        }).replace(' ', 'T') + '+0200';

                        const price = priceMap.get(formattedTimestamp);
                        
                        if (price !== undefined && !isNaN(consumption)) {
                            // Keep original price for display
                            const price_display = Number(price.toFixed(2));
                            // Add spot margin only for cost calculation
                            const cost = (consumption * (price + this.spotMargin)) / 100;

                            combinedData.push({
                                timestamp: formattedTimestamp,
                                consumption_kWh: Number(consumption.toFixed(3)),
                                price_cents_per_kWh: price_display,
                                cost_euros: Number(cost.toFixed(6))
                            });
                        }
                    }
                }
            }

            // Debug logging
            console.log(`Processed ${combinedData.length} combined data entries`);
            if (combinedData.length > 0) {
                console.log('First entry:', combinedData[0]);
                console.log('Last entry:', combinedData[combinedData.length - 1]);
            }

            // Sort by timestamp
            combinedData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

            // Convert to CSV
            const csvContent = [
                'timestamp,consumption_kWh,price_cents_per_kWh,cost_euros',
                ...combinedData.map(row => 
                    `${row.timestamp},${row.consumption_kWh},${row.price_cents_per_kWh},${row.cost_euros}`
                )
            ].join('\n');

            // Ensure processed directory exists
            const processedDir = path.join(process.cwd(), 'processed');
            await fs.mkdir(processedDir, { recursive: true });

            // Save combined data
            await fs.writeFile(
                path.join(processedDir, 'combined_data.csv'),
                csvContent
            );

            console.log('Data combination completed successfully');
        } catch (error) {
            console.error('Error combining data:', error);
            throw error;
        }
    }
}

module.exports = new DataProcessor();