// Helper function to parse CSV data
function parseCSV(csv) {
    const lines = csv.trim().split('\n');
    const headers = lines[0].split(',');
    return lines.slice(1).map(line => {
        const values = line.split(',');
        return headers.reduce((obj, header, index) => {
            obj[header] = values[index];
            return obj;
        }, {});
    });
}

// Function to update the analysis summary
function updateAnalysisSummary(data) {
    const summary = document.getElementById('analysisSummary');
    
    // Calculate total consumption and cost
    const totalConsumption = data.reduce((sum, row) => sum + parseFloat(row.consumption_kWh), 0);
    const totalCost = data.reduce((sum, row) => sum + parseFloat(row.cost_euros), 0);
    const avgPrice = data.reduce((sum, row) => sum + parseFloat(row.price_cents_per_kWh), 0) / data.length;

    summary.innerHTML = `
        <p><strong>Total Consumption:</strong> ${totalConsumption.toFixed(2)} kWh</p>
        <p><strong>Total Cost:</strong> ${totalCost.toFixed(2)} EUR</p>
        <p><strong>Average Price:</strong> ${avgPrice.toFixed(2)} cents/kWh</p>
    `;
}

// Function to create monthly charts
function createCharts(data) {
    // Group data by month
    const monthlyData = data.reduce((acc, row) => {
        const date = new Date(row.timestamp);
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        
        if (!acc[monthKey]) {
            acc[monthKey] = {
                consumption: 0,
                cost: 0,
                count: 0
            };
        }
        
        acc[monthKey].consumption += parseFloat(row.consumption_kWh);
        acc[monthKey].cost += parseFloat(row.cost_euros);
        acc[monthKey].count++;
        
        return acc;
    }, {});

    // Prepare data for charts
    const months = Object.keys(monthlyData);
    const consumptionValues = months.map(month => monthlyData[month].consumption);
    const costValues = months.map(month => monthlyData[month].cost);

    // Create consumption chart
    Plotly.newPlot('savingsChart', [{
        x: months,
        y: consumptionValues,
        type: 'bar',
        name: 'Monthly Consumption'
    }], {
        title: 'Monthly Electricity Consumption',
        xaxis: { title: 'Month' },
        yaxis: { title: 'Consumption (kWh)' }
    });

    // Create cost chart
    Plotly.newPlot('costChart', [{
        x: months,
        y: costValues,
        type: 'line',
        name: 'Monthly Cost'
    }], {
        title: 'Monthly Electricity Cost',
        xaxis: { title: 'Month' },
        yaxis: { title: 'Cost (EUR)' }
    });
}

// Function to fetch and update data
async function fetchData() {
    try {
        const response = await fetch('/api/analysis');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        
        document.getElementById('content').innerHTML = `
            <h2>Data Loaded</h2>
            <pre>${JSON.stringify(result, null, 2)}</pre>
        `;
    } catch (error) {
        console.error('Error fetching data:', error);
        document.getElementById('content').innerHTML = `
            <p style="color: red">Error loading data: ${error.message}</p>
        `;
    }
}

// Handle manual data update
document.getElementById('updateData').addEventListener('click', async () => {
    try {
        const button = document.getElementById('updateData');
        button.disabled = true;
        button.textContent = 'Updating...';
        
        await fetch('/api/update', { method: 'POST' });
        await fetchData();
        
        button.textContent = 'Update Data';
        button.disabled = false;
    } catch (error) {
        console.error('Error updating data:', error);
        alert('Failed to update data');
        button.textContent = 'Update Data';
        button.disabled = false;
    }
});

// Load data when page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('Page loaded, fetching data...');
    fetchData();
});