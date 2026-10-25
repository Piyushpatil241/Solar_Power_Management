import json
import sqlite3
import threading

import pandas as pd
import paho.mqtt.client as mqtt

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


# ========================================
# FASTAPI APPLICATION
# ========================================

app = FastAPI(
    title="Solar Power Management System",
    description="IoE Solar Energy Monitoring System",
    version="1.0"
)


# ========================================
# MQTT CONFIGURATION
# ========================================

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "solar/telemetry"


# ========================================
# DATABASE CONFIGURATION
# ========================================

DATABASE = "solar_data.db"


# ========================================
# LATEST TELEMETRY DATA
# ========================================

latest_data = {
    "solar_power": 0,
    "battery_voltage": 0,
    "battery_soc": 0,
    "load_power": 0,
    "essential_load": False,
    "non_essential_load": False,
    "mode": "UNKNOWN"
}


# ========================================
# INITIALIZE DATABASE
# ========================================

def initialize_database():

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            solar_power REAL,
            battery_voltage REAL,
            battery_soc REAL,
            load_power REAL,
            essential_load INTEGER,
            non_essential_load INTEGER,
            mode TEXT
        )
    """)

    connection.commit()
    connection.close()

    print("SQLite database initialized.")


initialize_database()


# ========================================
# SAVE TELEMETRY
# ========================================

def save_telemetry(data):

    connection = sqlite3.connect(DATABASE)

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO telemetry (
            timestamp,
            solar_power,
            battery_voltage,
            battery_soc,
            load_power,
            essential_load,
            non_essential_load,
            mode
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        pd.Timestamp.now().isoformat(),

        data.get("solar_power", 0),

        data.get("battery_voltage", 0),

        data.get("battery_soc", 0),

        data.get("load_power", 0),

        int(data.get("essential_load", False)),

        int(data.get("non_essential_load", False)),

        data.get("mode", "UNKNOWN")
    ))

    connection.commit()

    connection.close()


# ========================================
# MQTT CONNECT CALLBACK
# ========================================

def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    if reason_code == 0:

        print("Connected to MQTT broker!")

        client.subscribe(MQTT_TOPIC)

        print(
            f"Subscribed to: {MQTT_TOPIC}"
        )

    else:

        print(
            f"MQTT connection failed. "
            f"Code: {reason_code}"
        )


# ========================================
# MQTT MESSAGE CALLBACK
# ========================================

def on_message(
    client,
    userdata,
    msg
):

    global latest_data

    try:

        data = json.loads(
            msg.payload.decode()
        )

        latest_data = data

        print(
            "Received MQTT data:"
        )

        print(data)

        save_telemetry(data)

    except json.JSONDecodeError:

        print(
            "Invalid JSON received"
        )


# ========================================
# MQTT CLIENT
# ========================================

mqtt_client = mqtt.Client(
    callback_api_version=
    mqtt.CallbackAPIVersion.VERSION2
)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message


# ========================================
# MQTT BACKGROUND THREAD
# ========================================

def mqtt_loop():

    print("Connecting to MQTT...")

    mqtt_client.connect(
        MQTT_BROKER,
        MQTT_PORT,
        60
    )

    mqtt_client.loop_forever()


mqtt_thread = threading.Thread(
    target=mqtt_loop,
    daemon=True
)

mqtt_thread.start()


# ========================================
# STATIC FILES
# ========================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ========================================
# API: CURRENT DATA
# ========================================

@app.get("/api/data")
def get_data():

    return latest_data


# ========================================
# API: HISTORICAL DATA
# ========================================

@app.get("/api/history")
def get_history():

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            timestamp,
            solar_power,
            battery_voltage,
            battery_soc,
            load_power,
            essential_load,
            non_essential_load,
            mode
        FROM telemetry
        ORDER BY id DESC
        LIMIT 100
    """)

    rows = cursor.fetchall()

    connection.close()


    history = []


    for row in rows:

        history.append({

            "timestamp": row[0],

            "solar_power": row[1],

            "battery_voltage": row[2],

            "battery_soc": row[3],

            "load_power": row[4],

            "essential_load": bool(row[5]),

            "non_essential_load": bool(row[6]),

            "mode": row[7]

        })


    return history


# ========================================
# API: ANALYTICS
# ========================================

@app.get("/api/analytics")
def get_analytics():

    connection = sqlite3.connect(
        DATABASE
    )

    query = """
        SELECT
            timestamp,
            solar_power,
            load_power,
            battery_soc
        FROM telemetry
        ORDER BY timestamp
    """

    df = pd.read_sql_query(
        query,
        connection
    )

    connection.close()


    # ------------------------------------
    # No data
    # ------------------------------------

    if df.empty:

        return {
            "solar_energy_kwh": 0,
            "load_energy_kwh": 0,
            "energy_surplus_kwh": 0,
            "peak_solar_power": 0,
            "average_solar_power": 0,
            "average_load_power": 0,
            "solar_load_ratio": 0
        }


    # ------------------------------------
    # Convert timestamp
    # ------------------------------------

    df["timestamp"] = pd.to_datetime(
        df["timestamp"]
    )


    # ------------------------------------
    # Calculate time difference
    # ------------------------------------

    df["time_diff_hours"] = (
        df["timestamp"]
        .diff()
        .dt.total_seconds()
        / 3600
    )


    # ------------------------------------
    # Solar energy
    # Trapezoidal integration
    # ------------------------------------

    df["solar_energy_wh"] = (

        (
            df["solar_power"]
            + df["solar_power"].shift(1)
        )
        / 2

    ) * df["time_diff_hours"]


    # ------------------------------------
    # Load energy
    # Trapezoidal integration
    # ------------------------------------

    df["load_energy_wh"] = (

        (
            df["load_power"]
            + df["load_power"].shift(1)
        )
        / 2

    ) * df["time_diff_hours"]


    # ------------------------------------
    # Remove first row
    # ------------------------------------

    df = df.dropna(
        subset=[
            "solar_energy_wh",
            "load_energy_wh"
        ]
    )


    # ------------------------------------
    # Calculate analytics
    # ------------------------------------

    solar_energy_wh = (
        df["solar_energy_wh"].sum()
    )

    load_energy_wh = (
        df["load_energy_wh"].sum()
    )

    energy_surplus_wh = (
        solar_energy_wh
        - load_energy_wh
    )


    peak_solar_power = (
        df["solar_power"].max()
    )

    average_solar_power = (
        df["solar_power"].mean()
    )

    average_load_power = (
        df["load_power"].mean()
    )


    solar_load_ratio = (

        average_solar_power
        / average_load_power

        if average_load_power > 0
        else 0

    )


    # ------------------------------------
    # Return analytics
    # ------------------------------------

    return {

        "solar_energy_kwh":
            round(
                solar_energy_wh / 1000,
                6
            ),

        "load_energy_kwh":
            round(
                load_energy_wh / 1000,
                6
            ),

        "energy_surplus_kwh":
            round(
                energy_surplus_wh / 1000,
                6
            ),

        "peak_solar_power":
            round(
                peak_solar_power,
                2
            ),

        "average_solar_power":
            round(
                average_solar_power,
                2
            ),

        "average_load_power":
            round(
                average_load_power,
                2
            ),

        "solar_load_ratio":
            round(
                solar_load_ratio,
                2
            )
    }


# ========================================
# HOME PAGE
# ========================================

@app.get(
    "/",
    response_class=HTMLResponse
)
def home():

    with open(
        "templates/index.html",
        "r",
        encoding="utf-8"
    ) as file:

        return file.read()