import sqlite3
import pandas as pd


# ========================================
# CONFIGURATION
# ========================================

DATABASE = "solar_data.db"


# ========================================
# LOAD DATA FROM SQLITE
# ========================================

connection = sqlite3.connect(DATABASE)

query = """
SELECT *
FROM telemetry
ORDER BY timestamp
"""

df = pd.read_sql_query(query, connection)

connection.close()


# ========================================
# CHECK DATA
# ========================================

if df.empty:
    print("\nNo telemetry data available.")
    exit()


# ========================================
# PREPARE TIMESTAMP
# ========================================

df["timestamp"] = pd.to_datetime(df["timestamp"])


# ========================================
# CALCULATE TIME DIFFERENCE
# ========================================

df["time_diff_hours"] = (
    df["timestamp"].diff().dt.total_seconds()
    / 3600
)


# ========================================
# CALCULATE SOLAR ENERGY
# Trapezoidal integration
# ========================================

df["solar_energy_wh"] = (
    (
        df["solar_power"]
        + df["solar_power"].shift(1)
    )
    / 2
) * df["time_diff_hours"]


# ========================================
# CALCULATE LOAD ENERGY
# Trapezoidal integration
# ========================================

df["load_energy_wh"] = (
    (
        df["load_power"]
        + df["load_power"].shift(1)
    )
    / 2
) * df["time_diff_hours"]


# ========================================
# REMOVE FIRST ROW
# First row has no previous timestamp
# ========================================

df = df.dropna(
    subset=[
        "solar_energy_wh",
        "load_energy_wh"
    ]
)


# ========================================
# BASIC POWER ANALYTICS
# ========================================

average_solar = df["solar_power"].mean()
peak_solar = df["solar_power"].max()

average_load = df["load_power"].mean()
peak_load = df["load_power"].max()

average_soc = df["battery_soc"].mean()
minimum_soc = df["battery_soc"].min()


# ========================================
# ENERGY ANALYTICS
# ========================================

total_solar_energy = df["solar_energy_wh"].sum()
total_load_energy = df["load_energy_wh"].sum()

solar_energy_wh = total_solar_energy
load_energy_wh = total_load_energy

solar_energy_kwh = solar_energy_wh / 1000
load_energy_kwh = load_energy_wh / 1000

energy_surplus = solar_energy_wh - load_energy_wh


# ========================================
# POWER RATIO
# ========================================

solar_load_ratio = (
    average_solar / average_load
    if average_load > 0
    else 0
)


# ========================================
# DISPLAY RESULTS
# ========================================

print("\n========================================")
print("       SOLAR ENERGY ANALYTICS")
print("========================================\n")

print(f"Telemetry readings       : {len(df) + 1}")

print(f"Average solar power      : {average_solar:.2f} W")
print(f"Peak solar power         : {peak_solar:.2f} W")

print(f"Average load power       : {average_load:.2f} W")
print(f"Peak load power          : {peak_load:.2f} W")

print(f"Average battery SOC      : {average_soc:.2f}%")
print(f"Minimum battery SOC      : {minimum_soc:.2f}%")


print("\n------------- ENERGY -------------\n")

print(f"Solar energy generated   : {solar_energy_wh:.4f} Wh")
print(f"Solar energy generated   : {solar_energy_kwh:.6f} kWh")

print(f"Load energy consumed     : {load_energy_wh:.4f} Wh")
print(f"Load energy consumed     : {load_energy_kwh:.6f} kWh")

print(f"Energy surplus           : {energy_surplus:.4f} Wh")


print("\n------------- RATIOS -------------\n")

print(f"Solar / Load ratio       : {solar_load_ratio:.2f}")


print("\n========================================")