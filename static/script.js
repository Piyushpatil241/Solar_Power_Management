let powerChart = null;


// ========================================
// FETCH CURRENT DATA
// ========================================

async function fetchCurrentData() {
    try {
        const response = await fetch("/api/data");
        const data = await response.json();

        updateDashboard(data);

    } catch (error) {
        console.error("Error fetching current data:", error);
    }
}


// ========================================
// UPDATE DASHBOARD
// ========================================

function updateDashboard(data) {

    // Solar
    document.getElementById("solarPower").textContent =
        `${Number(data.solar_power).toFixed(1)} W`;

    // Battery
    document.getElementById("batterySOC").textContent =
        `${Number(data.battery_soc).toFixed(1)}%`;

    document.getElementById("batteryVoltage").textContent =
        `${Number(data.battery_voltage).toFixed(2)} V`;

    document.getElementById("batteryFill").style.width =
        `${Math.min(Math.max(data.battery_soc, 0), 100)}%`;

    // Load
    document.getElementById("loadPower").textContent =
        `${Number(data.load_power).toFixed(1)} W`;


    // ========================================
    // LOAD STATUS
    // ========================================

    const essentialElement =
        document.getElementById("essentialLoad");

    const nonEssentialElement =
        document.getElementById("nonEssentialLoad");


    if (essentialElement) {
        essentialElement.textContent =
            data.essential_load ? "ON" : "OFF";

        essentialElement.className =
            data.essential_load
                ? "load-indicator on"
                : "load-indicator off";
    }


    if (nonEssentialElement) {
        nonEssentialElement.textContent =
            data.non_essential_load ? "ON" : "OFF";

        nonEssentialElement.className =
            data.non_essential_load
                ? "load-indicator on"
                : "load-indicator off";
    }


    // ========================================
    // POWER FLOW
    // ========================================

    const flowSolar =
        document.getElementById("flowSolar");

    const flowLoad =
        document.getElementById("flowLoad");

    const flowBattery =
        document.getElementById("flowBattery");


    if (flowSolar) {
        flowSolar.textContent =
            `${Number(data.solar_power).toFixed(1)} W`;
    }

    if (flowLoad) {
        flowLoad.textContent =
            `${Number(data.load_power).toFixed(1)} W`;
    }

    if (flowBattery) {
        flowBattery.textContent =
            `${Number(data.battery_voltage).toFixed(2)} V`;
    }
}

async function fetchAnalytics() {
    try {
        const response = await fetch("/api/analytics");
        const data = await response.json();

        document.getElementById("energyGenerated").textContent =
            Number(data.solar_energy_kwh).toFixed(3);

        document.getElementById("energyConsumed").textContent =
            Number(data.load_energy_kwh).toFixed(3);

        document.getElementById("energySurplus").textContent =
            Number(data.energy_surplus_kwh).toFixed(3);

        document.getElementById("peakSolar").textContent =
            Number(data.peak_solar_power).toFixed(1);

        document.getElementById("averageSolar").textContent =
            Number(data.average_solar_power).toFixed(1);

        document.getElementById("averageLoad").textContent =
            Number(data.average_load_power).toFixed(1);

        document.getElementById("solarLoadRatio").textContent =
            Number(data.solar_load_ratio).toFixed(2);

    } catch (error) {
        console.error(
            "Error fetching analytics:",
            error
        );
    }
}


// ========================================
// FETCH HISTORICAL DATA
// ========================================

async function fetchHistory() {

    try {

        const response = await fetch("/api/history");

        const history = await response.json();

        // API returns newest → oldest.
        // Reverse it for chronological plotting.
        history.reverse();

        updatePowerChart(history);

    } catch (error) {

        console.error(
            "Error fetching historical data:",
            error
        );

    }
}


// ========================================
// CREATE / UPDATE POWER CHART
// ========================================

function updatePowerChart(history) {

    const canvas =
        document.getElementById("powerChart");

    if (!canvas) {
        console.error("powerChart canvas not found.");
        return;
    }


    const labels = history.map(item => {

        const date =
            new Date(item.timestamp);

        return date.toLocaleTimeString(
            [],
            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            }
        );

    });


    const solarData = history.map(
        item => Number(item.solar_power)
    );

    const loadData = history.map(
        item => Number(item.load_power)
    );


    // ========================================
    // CREATE CHART
    // ========================================

    if (!powerChart) {

        powerChart = new Chart(
            canvas.getContext("2d"),
            {
                type: "line",

                data: {
                    labels: labels,

                    datasets: [

                        {
                            label: "Solar Generation",

                            data: solarData,

                            borderWidth: 2,

                            tension: 0.3,

                            fill: false
                        },

                        {
                            label: "Load Consumption",

                            data: loadData,

                            borderWidth: 2,

                            tension: 0.3,

                            fill: false
                        }

                    ]
                },


                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    interaction: {
                        mode: "index",
                        intersect: false
                    },

                    plugins: {

                        legend: {
                            display: true
                        },

                        tooltip: {
                            enabled: true
                        }

                    },


                    scales: {

                        x: {
                            title: {
                                display: true,
                                text: "Time"
                            }
                        },

                        y: {

                            beginAtZero: true,

                            title: {
                                display: true,
                                text: "Power (W)"
                            }

                        }

                    }

                }

            }
        );

    }

    // ========================================
    // UPDATE EXISTING CHART
    // ========================================

    else {

        powerChart.data.labels = labels;

        powerChart.data.datasets[0].data =
            solarData;

        powerChart.data.datasets[1].data =
            loadData;

        powerChart.update();

    }
}


// ========================================
// INITIAL LOAD
// ========================================

fetchCurrentData();
fetchHistory();
fetchAnalytics();


// ========================================
// REFRESH CURRENT DATA
// ========================================

setInterval(
    fetchCurrentData,
    1000
);


// ========================================
// REFRESH HISTORICAL CHART
// ========================================

// MQTT publishes every ~5 seconds.
// Updating the history every 5 seconds
// keeps the chart synchronized with SQLite.
setInterval(
    fetchCurrentData, 
    1000
);

setInterval(
    fetchHistory,
    5000
);

setInterval(
    fetchAnalytics,
    5000
);