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
    const metrics = document.getElementById('metrics');
    
    try {
        // Calculate metrics with error handling
        const totalConsumption = data.reduce((sum, row) => sum + (parseFloat(row.consumption_kWh) || 0), 0);
        const totalCost = data.reduce((sum, row) => sum + (parseFloat(row.cost_euros) || 0), 0);
        const validPrices = data.filter(row => !isNaN(parseFloat(row.price_cents_per_kWh)));
        const avgPrice = validPrices.length > 0 
            ? validPrices.reduce((sum, row) => sum + parseFloat(row.price_cents_per_kWh), 0) / validPrices.length 
            : 0;
        
        // Find max and min consumption times with validation
        const consumptionData = data
            .map(row => ({
                timestamp: row.timestamp.includes('T') ? new Date(row.timestamp) : new Date(row.timestamp.replace(' ', 'T')),
                consumption: parseFloat(row.consumption_kWh) || 0
            }))
            .filter(d => !isNaN(d.timestamp.getTime()) && !isNaN(d.consumption));

        console.log('Processed consumption data:', consumptionData);

        if (consumptionData.length === 0) {
            console.error('No valid consumption data after processing');
            metrics.innerHTML = '<div class="metric-card"><h3>Error</h3><h2>No valid consumption data found</h2></div>';
            return;
        }

        const maxConsumption = Math.max(...consumptionData.map(d => d.consumption));
        const maxConsumptionEntry = consumptionData.find(d => d.consumption === maxConsumption);

        // Update metrics display
        metrics.innerHTML = `
            <div class="metric-card">
                <h3>Total Consumption</h3>
                <h2>${totalConsumption.toFixed(1)} kWh</h2>
            </div>
            <div class="metric-card">
                <h3>Total Cost</h3>
                <h2>${totalCost.toFixed(2)} €</h2>
            </div>
            <div class="metric-card">
                <h3>Average Price</h3>
                <h2>${avgPrice.toFixed(2)} c/kWh</h2>
            </div>
            <div class="metric-card">
                <h3>Peak Usage</h3>
                <h2>${maxConsumption.toFixed(2)} kWh</h2>
                <small>${maxConsumptionEntry.timestamp.toLocaleString()}</small>
            </div>
        `;
    } catch (error) {
        console.error('Error updating analysis summary:', error);
        metrics.innerHTML = `
            <div class="metric-card">
                <h3>Error</h3>
                <h2>Failed to calculate metrics</h2>
                <small>Check console for details</small>
            </div>
        `;
    }
}

// Modify the Plotly config
const config = {
    responsive: true,
    useResizeHandler: true,
    displayModeBar: false,
    displaylogo: false
};

// Update the resize function
function resizeChart(chartElement) {
    if (chartElement && chartElement.firstElementChild) {
        const plotlyDiv = chartElement.firstElementChild;
        const containerWidth = chartElement.clientWidth;
        const containerHeight = chartElement.clientHeight;
        
        Plotly.relayout(plotlyDiv, {
            width: containerWidth,
            height: containerHeight
        });
    }
}

// Function to initialize chart after creation
function initializeChart(chartId) {
    return new Promise(resolve => {
        const chartElement = document.getElementById(chartId);
        if (chartElement) {
            // Wait for next frame to ensure DOM is ready
            requestAnimationFrame(() => {
                const plotlyDiv = chartElement.firstElementChild;
                if (plotlyDiv) {
                    const containerWidth = chartElement.clientWidth;
                    const containerHeight = chartElement.clientHeight;
                    
                    Plotly.relayout(plotlyDiv, {
                        width: containerWidth,
                        height: containerHeight
                    }).then(resolve);
                } else {
                    resolve();
                }
            });
        } else {
            resolve();
        }
    });
}

// Update createCharts function to handle async initialization properly
async function createCharts(data) {
    const chartType = window.CHART_TYPE || 'overview';
    
    try {
        switch (chartType) {
            case 'overview':
                const metricsElement = document.getElementById('metrics');
                if (metricsElement) {
                    updateAnalysisSummary(data);
                }
                await createConsumptionChart(data);
                await createCostChart(data);
                await Promise.all([
                    initializeChart('savingsChart'),
                    initializeChart('costChart')
                ]);
                break;
            case 'consumption':
                await createConsumptionChart(data);
                await initializeChart('savingsChart');
                break;
            case 'prices':
                await createPriceChart(data);
                await initializeChart('priceChart');
                break;
            case 'patterns':
                await createHourlyChart(data);
                await initializeChart('hourlyChart');
                break;
        }
    } catch (error) {
        console.error('Error creating charts:', error);
        const errorElement = document.getElementById('error');
        if (errorElement) {
            errorElement.innerHTML = `
                <p style="color: red">Error creating charts: ${error.message}</p>
            `;
            errorElement.style.display = 'block';
        }
    }
}

// Split existing chart creation code into separate functions
function createConsumptionChart(data) {
    return new Promise((resolve, reject) => {
        try {
            // Group data by day and month with proper data validation
            const dailyData = data.reduce((acc, row) => {
                if (!row.timestamp) return acc;
                
                const date = new Date(row.timestamp);
                if (isNaN(date.getTime())) return acc;
                
                const dayKey = date.toISOString().split('T')[0];
                const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
                
                if (!acc[dayKey]) {
                    acc[dayKey] = {
                        consumption: 0,
                        cost: 0,
                        month: monthKey
                    };
                }
                
                const consumption = parseFloat(row.consumption_kWh) || 0;
                const cost = parseFloat(row.cost_euros) || 0;
                
                acc[dayKey].consumption += consumption;
                acc[dayKey].cost += cost;
                
                return acc;
            }, {});

            // Calculate monthly cumulative data
            const monthlyGroups = {};
            Object.entries(dailyData).forEach(([day, data]) => {
                if (!monthlyGroups[data.month]) {
                    monthlyGroups[data.month] = {
                        days: [],
                        consumptions: [],
                        cumulative: []
                    };
                }
                monthlyGroups[data.month].days.push(day);
                monthlyGroups[data.month].consumptions.push(data.consumption);
            });

            // Calculate cumulative values for each month
            Object.values(monthlyGroups).forEach(month => {
                let sum = 0;
                month.cumulative = month.consumptions.map(v => sum += v);
            });

            // Flatten data for plotting
            const allDays = [];
            const allConsumptions = [];
            const allCumulative = [];
            const monthMarkers = [];
            const monthlyCosts = {};
            
            Object.entries(monthlyGroups).forEach(([month, data]) => {
                allDays.push(...data.days);
                allConsumptions.push(...data.consumptions);
                allCumulative.push(...data.cumulative);
                
                // Calculate monthly totals for cost chart
                monthlyCosts[month] = {
                    consumption: data.consumptions.reduce((sum, val) => sum + val, 0),
                    cost: Object.entries(dailyData)
                        .filter(([day]) => day.startsWith(month))
                        .reduce((sum, [_, dayData]) => sum + dayData.cost, 0)
                };
                
                monthMarkers.push({
                    type: 'line',
                    x0: data.days[0],
                    x1: data.days[0],
                    y0: 0,
                    y1: Math.max(...data.cumulative),
                    line: {
                        color: '#404040',
                        width: 1,
                        dash: 'dash'
                    }
                });
            });

            // Update the Grafana-style theme with responsive configuration
            const layout = {
                paper_bgcolor: '#181b1f',
                plot_bgcolor: '#181b1f',
                font: { 
                    color: '#d8d9da',
                    size: 12
                },
                margin: { 
                    t: 40, 
                    r: 50, 
                    b: 40, 
                    l: 60 
                },
                xaxis: {
                    gridcolor: '#404040',
                    linecolor: '#404040',
                    tickangle: 45,
                    automargin: true
                },
                yaxis: {
                    gridcolor: '#404040',
                    linecolor: '#404040',
                    automargin: true
                },
                shapes: monthMarkers,
                showlegend: true,
                legend: {
                    bgcolor: '#181b1f',
                    bordercolor: '#404040',
                    orientation: 'h',
                    yanchor: 'bottom',
                    y: 1.02,
                    xanchor: 'right',
                    x: 1
                },
                autosize: true,
                responsive: true
            };

            // Consumption chart with daily bars and monthly cumulative
            Plotly.newPlot('savingsChart', [
                {
                    x: allDays,
                    y: allConsumptions,
                    type: 'bar',
                    name: 'Daily Consumption',
                    marker: { color: '#3274D9' },
                    yaxis: 'y'
                },
                {
                    x: allDays,
                    y: allCumulative,
                    type: 'scatter',
                    name: 'Monthly Cumulative',
                    line: { color: '#FF9830', shape: 'spline' },
                    yaxis: 'y2'
                }
            ], {
                ...layout,
                title: 'Daily Electricity Consumption with Monthly Cumulative',
                yaxis: { 
                    ...layout.yaxis,
                    title: 'Daily kWh',
                    range: [0, Math.max(...allConsumptions) * 1.1], // Add 10% padding
                    side: 'left'
                },
                yaxis2: {
                    title: 'Cumulative kWh',
                    overlaying: 'y',
                    side: 'right',
                    range: [0, Math.max(...allCumulative) * 1.05], // Add 5% padding
                    gridcolor: '#404040',
                    linecolor: '#404040',
                    showgrid: false // Hide grid for second axis to avoid clutter
                }
            }, config).then(resolve).catch(reject);
        } catch (error) {
            reject(error);
        }
    });
}

function createCostChart(data) {
    // Group data by day and month
    const dailyData = data.reduce((acc, row) => {
        const date = new Date(row.timestamp);
        const dayKey = date.toISOString().split('T')[0];
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        
        if (!acc[dayKey]) {
            acc[dayKey] = {
                consumption: 0,
                cost: 0,
                month: monthKey
            };
        }
        
        acc[dayKey].consumption += parseFloat(row.consumption_kWh);
        acc[dayKey].cost += parseFloat(row.cost_euros);
        
        return acc;
    }, {});

    // Calculate monthly cumulative data
    const monthlyGroups = {};
    Object.entries(dailyData).forEach(([day, data]) => {
        if (!monthlyGroups[data.month]) {
            monthlyGroups[data.month] = {
                days: [],
                consumptions: [],
                cumulative: []
            };
        }
        monthlyGroups[data.month].days.push(day);
        monthlyGroups[data.month].consumptions.push(data.consumption);
    });

    // Calculate cumulative values for each month
    Object.values(monthlyGroups).forEach(month => {
        let sum = 0;
        month.cumulative = month.consumptions.map(v => sum += v);
    });

    // Flatten data for plotting
    const allDays = [];
    const allConsumptions = [];
    const allCumulative = [];
    const monthMarkers = [];
    const monthlyCosts = {};
    
    Object.entries(monthlyGroups).forEach(([month, data]) => {
        allDays.push(...data.days);
        allConsumptions.push(...data.consumptions);
        allCumulative.push(...data.cumulative);
        
        // Calculate monthly totals for cost chart
        monthlyCosts[month] = {
            consumption: data.consumptions.reduce((sum, val) => sum + val, 0),
            cost: Object.entries(dailyData)
                .filter(([day]) => day.startsWith(month))
                .reduce((sum, [_, dayData]) => sum + dayData.cost, 0)
        };
        
        monthMarkers.push({
            type: 'line',
            x0: data.days[0],
            x1: data.days[0],
            y0: 0,
            y1: Math.max(...data.cumulative),
            line: {
                color: '#404040',
                width: 1,
                dash: 'dash'
            }
        });
    });

    // Update the Grafana-style theme with responsive configuration
    const layout = {
        paper_bgcolor: '#181b1f',
        plot_bgcolor: '#181b1f',
        font: { 
            color: '#d8d9da',
            size: 12
        },
        margin: { 
            t: 40, 
            r: 50, 
            b: 40, 
            l: 60 
        },
        xaxis: {
            gridcolor: '#404040',
            linecolor: '#404040',
            tickangle: 45,
            automargin: true
        },
        yaxis: {
            gridcolor: '#404040',
            linecolor: '#404040',
            automargin: true
        },
        shapes: monthMarkers,
        showlegend: true,
        legend: {
            bgcolor: '#181b1f',
            bordercolor: '#404040',
            orientation: 'h',
            yanchor: 'bottom',
            y: 1.02,
            xanchor: 'right',
            x: 1
        },
        autosize: true,
        responsive: true
    };

    // Cost chart with price overlay
    const months = Object.keys(monthlyCosts);
    const costValues = months.map(m => monthlyCosts[m].cost);
    const avgPrices = months.map(m => 
        (monthlyCosts[m].cost / monthlyCosts[m].consumption) * 100 // Convert to cents/kWh
    );

    Plotly.newPlot('costChart', [
        {
            x: months,
            y: costValues,
            type: 'scatter',
            name: 'Cost',
            line: { color: '#73BF69' }
        },
        {
            x: months,
            y: avgPrices,
            type: 'scatter',
            name: 'Avg Price',
            yaxis: 'y2',
            line: { color: '#FF9830' }
        }
    ], {
        ...layout,
        title: 'Monthly Cost and Average Price',
        yaxis: { ...layout.yaxis, title: 'EUR' },
        yaxis2: {
            title: 'cents/kWh',
            overlaying: 'y',
            side: 'right',
            gridcolor: '#404040',
            linecolor: '#404040'
        }
    }, config);
}

function createPriceChart(data) {
    // Group data by day and month
    const dailyData = data.reduce((acc, row) => {
        const date = new Date(row.timestamp);
        const dayKey = date.toISOString().split('T')[0];
        const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
        
        if (!acc[dayKey]) {
            acc[dayKey] = {
                consumption: 0,
                cost: 0,
                month: monthKey
            };
        }
        
        acc[dayKey].consumption += parseFloat(row.consumption_kWh);
        acc[dayKey].cost += parseFloat(row.cost_euros);
        
        return acc;
    }, {});

    // Calculate monthly cumulative data
    const monthlyGroups = {};
    Object.entries(dailyData).forEach(([day, data]) => {
        if (!monthlyGroups[data.month]) {
            monthlyGroups[data.month] = {
                days: [],
                consumptions: [],
                cumulative: []
            };
        }
        monthlyGroups[data.month].days.push(day);
        monthlyGroups[data.month].consumptions.push(data.consumption);
    });

    // Calculate cumulative values for each month
    Object.values(monthlyGroups).forEach(month => {
        let sum = 0;
        month.cumulative = month.consumptions.map(v => sum += v);
    });

    // Flatten data for plotting
    const allDays = [];
    const allConsumptions = [];
    const allCumulative = [];
    const monthMarkers = [];
    const monthlyCosts = {};
    
    Object.entries(monthlyGroups).forEach(([month, data]) => {
        allDays.push(...data.days);
        allConsumptions.push(...data.consumptions);
        allCumulative.push(...data.cumulative);
        
        // Calculate monthly totals for cost chart
        monthlyCosts[month] = {
            consumption: data.consumptions.reduce((sum, val) => sum + val, 0),
            cost: Object.entries(dailyData)
                .filter(([day]) => day.startsWith(month))
                .reduce((sum, [_, dayData]) => sum + dayData.cost, 0)
        };
        
        monthMarkers.push({
            type: 'line',
            x0: data.days[0],
            x1: data.days[0],
            y0: 0,
            y1: Math.max(...data.cumulative),
            line: {
                color: '#404040',
                width: 1,
                dash: 'dash'
            }
        });
    });

    // Update the Grafana-style theme with responsive configuration
    const layout = {
        paper_bgcolor: '#181b1f',
        plot_bgcolor: '#181b1f',
        font: { 
            color: '#d8d9da',
            size: 12
        },
        margin: { 
            t: 40, 
            r: 50, 
            b: 40, 
            l: 60 
        },
        xaxis: {
            gridcolor: '#404040',
            linecolor: '#404040',
            tickangle: 45,
            automargin: true
        },
        yaxis: {
            gridcolor: '#404040',
            linecolor: '#404040',
            automargin: true
        },
        shapes: monthMarkers,
        showlegend: true,
        legend: {
            bgcolor: '#181b1f',
            bordercolor: '#404040',
            orientation: 'h',
            yanchor: 'bottom',
            y: 1.02,
            xanchor: 'right',
            x: 1
        },
        autosize: true,
        responsive: true
    };

    // Create price chart with daily values and monthly cumulative
    const dailyPrices = allDays.map((day, index) => {
        const dayData = data.filter(row => row.timestamp.startsWith(day));
        return {
            day,
            avgPrice: dayData.reduce((sum, row) => sum + parseFloat(row.price_cents_per_kWh), 0) / dayData.length
        };
    });

    const monthlyPriceCumulative = {};
    let currentMonth = '';
    let cumulative = [];

    dailyPrices.forEach(({ day, avgPrice }) => {
        const month = day.substring(0, 7);
        if (month !== currentMonth) {
            currentMonth = month;
            cumulative = [];
        }
        cumulative.push((cumulative.length ? cumulative[cumulative.length - 1] : 0) + avgPrice);
        monthlyPriceCumulative[day] = cumulative[cumulative.length - 1];
    });

    Plotly.newPlot('priceChart', [
        {
            x: dailyPrices.map(d => d.day),
            y: dailyPrices.map(d => d.avgPrice),
            type: 'bar',
            name: 'Daily Price',
            marker: { color: '#E02F44' },
            yaxis: 'y'
        },
        {
            x: Object.keys(monthlyPriceCumulative),
            y: Object.values(monthlyPriceCumulative),
            type: 'scatter',
            name: 'Monthly Cumulative',
            line: { color: '#FF9830', shape: 'spline' },
            yaxis: 'y2'
        }
    ], {
        ...layout,
        title: 'Daily Electricity Price with Monthly Cumulative',
        yaxis: { 
            ...layout.yaxis,
            title: 'cents/kWh',
            range: [0, Math.max(...dailyPrices.map(d => d.avgPrice)) * 1.1]
        },
        yaxis2: {
            title: 'Cumulative cents/kWh',
            overlaying: 'y',
            side: 'right',
            range: [0, Math.max(...Object.values(monthlyPriceCumulative)) * 1.05],
            gridcolor: '#404040',
            linecolor: '#404040',
            showgrid: false
        }
    }, config);
}

function processHourlyData(data) {
    const hours = Array.from({length: 24}, (_, i) => String(i).padStart(2, '0'));
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    
    // Initialize aggregation arrays
    const aggregatedData = {};
    days.forEach((day, dayIndex) => {
        aggregatedData[day] = {};
        hours.forEach(hour => {
            aggregatedData[day][hour] = {
                total: 0,
                count: 0,
                avg: 0
            };
        });
    });

    // Aggregate data by weekday and hour
    data.forEach(row => {
        const date = new Date(row.timestamp);
        const dayOfWeek = days[((date.getDay() + 6) % 7)]; // Convert to Monday=0, Sunday=6
        const hour = String(date.getHours()).padStart(2, '0');
        const consumption = parseFloat(row.consumption_kWh);
        
        if (!isNaN(consumption)) {
            aggregatedData[dayOfWeek][hour].total += consumption;
            aggregatedData[dayOfWeek][hour].count++;
        }
    });

    // Calculate averages
    days.forEach(day => {
        hours.forEach(hour => {
            const hourData = aggregatedData[day][hour];
            hourData.avg = hourData.count ? hourData.total / hourData.count : 0;
        });
    });

    return { aggregatedData, hours, days };
}

function createHourlyChart(data) {
    const hourlyData = processHourlyData(data);
    
    // Prepare data for heatmap
    const zValues = hourlyData.days.map(day => 
        hourlyData.hours.map(hour => hourlyData.aggregatedData[day][hour].avg)
    );

    const customData = hourlyData.days.map(day => 
        hourlyData.hours.map(hour => [
            hourlyData.aggregatedData[day][hour].total,
            hourlyData.aggregatedData[day][hour].count
        ])
    );

    // Update the Grafana-style theme with responsive configuration
    const layout = {
        paper_bgcolor: '#181b1f',
        plot_bgcolor: '#181b1f',
        font: { 
            color: '#d8d9da',
            size: 12
        },
        margin: { 
            t: 40, 
            r: 50, 
            b: 40, 
            l: 60 
        },
        title: 'Weekly Consumption Pattern by Hour',
        xaxis: { 
            title: 'Day of Week',
            tickangle: 0,
            gridcolor: '#404040',
            linecolor: '#404040'
        },
        yaxis: { 
            title: 'Hour of Day',
            autorange: 'reversed',
            gridcolor: '#404040',
            linecolor: '#404040'
        },
        autosize: true,
        responsive: true
    };

    Plotly.newPlot('hourlyChart', [{
        z: zValues,
        x: hourlyData.days,
        y: hourlyData.hours.map(h => `${h}:00`),
        type: 'heatmap',
        colorscale: 'Viridis',
        hoverongaps: false,
        hovertemplate: 
            'Day: %{x}<br>' +
            'Hour: %{y}<br>' +
            'Average: %{z:.2f} kWh<br>' +
            'Total: %{customdata[0]:.1f} kWh<br>' +
            'Samples: %{customdata[1]}<br>' +
            '<extra></extra>',
        customdata: customData
    }], layout, config);
}

// Function to fetch and update data
async function fetchData() {
    const loadingElement = document.getElementById('loading');
    const contentElement = document.getElementById('content');
    const errorElement = document.getElementById('error');

    if (!loadingElement || !contentElement || !errorElement) {
        console.error('Required elements not found');
        return;
    }

    try {
        loadingElement.style.display = 'block';
        contentElement.style.display = 'none';
        errorElement.style.display = 'none';

        // First check if we need to update the data
        const response = await fetch('/api/analysis');
        if (!response.ok) {
            if (response.status === 404) {
                console.log('No data found, triggering initial update...');
                await fetch('/api/update', { method: 'POST' });
                // Fetch the data again after update
                const updatedResponse = await fetch('/api/analysis');
                if (!updatedResponse.ok) {
                    throw new Error(`HTTP error after update! status: ${updatedResponse.status}`);
                }
                const result = await updatedResponse.json();
                return await processData(result, loadingElement, contentElement, errorElement);
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        return await processData(result, loadingElement, contentElement, errorElement);

    } catch (error) {
        console.error('Error fetching data:', error);
        errorElement.innerHTML = `
            <p style="color: red">Error loading data: ${error.message}</p>
        `;
        errorElement.style.display = 'block';
        loadingElement.style.display = 'none';
        contentElement.style.display = 'none';
    }
}

// Helper function to process the fetched data
async function processData(result, loadingElement, contentElement, errorElement) {
    // Debug the data
    console.log('Raw CSV data:', result.data);
    
    // Parse and validate the data
    const parsedData = parseCSV(result.data);
    console.log('Parsed data:', parsedData);
    
    // Ensure all required fields exist and have valid values
    const data = parsedData
        .map(row => ({
            timestamp: row.timestamp,
            consumption_kWh: parseFloat(row.consumption_kWh),
            price_cents_per_kWh: parseFloat(row.price_cents_per_kWh),
            cost_euros: parseFloat(row.cost_euros)
        }))
        .filter(row => 
            row.timestamp && 
            !isNaN(row.consumption_kWh) && 
            !isNaN(row.price_cents_per_kWh) && 
            !isNaN(row.cost_euros)
        );

    console.log('Validated data:', data);
    console.log('Number of valid records:', data.length);

    if (data.length === 0) {
        throw new Error('No valid data records found after parsing');
    }

    // Hide loading before creating charts
    loadingElement.style.display = 'none';
    // Show content immediately
    contentElement.style.display = 'block';

    // Create charts after DOM update
    setTimeout(async () => {
        try {
            await createCharts(data);
        } catch (error) {
            console.error('Error creating charts:', error);
            errorElement.innerHTML = `
                <p style="color: red">Error creating charts: ${error.message}</p>
            `;
            errorElement.style.display = 'block';
        }
    }, 0);
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

// Update window resize handler with debouncing
let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        const charts = document.querySelectorAll('.chart-container');
        charts.forEach(resizeChart);
    }, 100);
});