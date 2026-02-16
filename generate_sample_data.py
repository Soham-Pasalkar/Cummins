"""
Sample PUMA Test Data Generator
Generates realistic test data for demonstration purposes
"""

import pandas as pd
import numpy as np
from datetime import datetime

def generate_transient_test(frequency='1Hz', duration=1800, num_sensors=50):
    """
    Generate sample transient test data
    
    Parameters:
    - frequency: '1Hz', '3Hz', or '10Hz'
    - duration: Test duration in seconds (default 1800 for transient)
    - num_sensors: Number of sensor columns to generate
    """
    
    # Calculate sampling rate
    freq_map = {'1Hz': 1, '3Hz': 3, '10Hz': 10}
    sample_rate = freq_map.get(frequency, 1)
    
    # Generate time array
    num_points = duration * sample_rate
    time = np.linspace(0, duration, num_points)
    
    # Create base dataframe
    data = {'Time': time}
    
    # Generate realistic sensor patterns
    
    # Engine Speed (varies in transient cycle)
    base_speed = 1200
    speed_variation = 400 * np.sin(2 * np.pi * time / 300) + 200 * np.sin(2 * np.pi * time / 100)
    noise = np.random.normal(0, 10, num_points)
    data['EngineSpeed_rpm'] = base_speed + speed_variation + noise
    
    # Engine Torque (correlated with speed)
    base_torque = 1500
    torque_variation = 800 * np.sin(2 * np.pi * time / 300 + 0.5) + 300 * np.sin(2 * np.pi * time / 150)
    noise = np.random.normal(0, 20, num_points)
    data['EngineTorque_Nm'] = np.clip(base_torque + torque_variation + noise, 0, 3000)
    
    # Coolant Temperature (slow rising trend)
    base_temp = 80
    temp_rise = 15 * (1 - np.exp(-time / 600))
    temp_variation = 3 * np.sin(2 * np.pi * time / 400)
    noise = np.random.normal(0, 0.5, num_points)
    data['CoolantTemp_C'] = base_temp + temp_rise + temp_variation + noise
    
    # Oil Temperature (similar to coolant but offset)
    data['OilTemp_C'] = data['CoolantTemp_C'] + 10 + np.random.normal(0, 1, num_points)
    
    # Oil Pressure (correlated with speed)
    base_press = 350
    press_variation = 150 * (data['EngineSpeed_rpm'] - 1200) / 600
    noise = np.random.normal(0, 5, num_points)
    data['OilPressure_kPa'] = base_press + press_variation + noise
    
    # Intake Pressure (boost pressure, correlated with load)
    base_intake = 130
    intake_variation = 80 * (data['EngineTorque_Nm'] - 1000) / 2000
    noise = np.random.normal(0, 3, num_points)
    data['IntakePress_kPa'] = np.clip(base_intake + intake_variation + noise, 95, 250)
    
    # Exhaust Pressure
    data['ExhaustPress_kPa'] = data['IntakePress_kPa'] * 1.4 + np.random.normal(0, 5, num_points)
    
    # Intake Temperature
    base_intake_temp = 40
    temp_variation = 20 * (data['IntakePress_kPa'] - 130) / 120
    noise = np.random.normal(0, 2, num_points)
    data['IntakeTemp_C'] = base_intake_temp + temp_variation + noise
    
    # Exhaust Temperature (high, correlated with load and speed)
    base_exhaust = 400
    exhaust_variation = 250 * (data['EngineTorque_Nm'] - 1000) / 2000
    exhaust_variation += 50 * np.sin(2 * np.pi * time / 300)
    noise = np.random.normal(0, 10, num_points)
    data['ExhaustTemp_C'] = np.clip(base_exhaust + exhaust_variation + noise, 200, 750)
    
    # Turbo Speed (high RPM, correlated with boost)
    base_turbo = 80000
    turbo_variation = 80000 * (data['IntakePress_kPa'] - 130) / 120
    noise = np.random.normal(0, 1000, num_points)
    data['TurboSpeed_rpm'] = np.clip(base_turbo + turbo_variation + noise, 0, 200000)
    
    # Fuel Pressure (high pressure, stable)
    base_fuel_press = 1200
    fuel_variation = 400 * (data['EngineTorque_Nm'] - 1000) / 2000
    noise = np.random.normal(0, 20, num_points)
    data['FuelPressure_bar'] = np.clip(base_fuel_press + fuel_variation + noise, 300, 1800)
    
    # Fuel Temperature
    data['FuelTemp_C'] = 45 + 10 * (1 - np.exp(-time / 800)) + np.random.normal(0, 1, num_points)
    
    # Fuel Rate (correlated with torque and speed)
    base_fuel_rate = 40
    fuel_rate_variation = 80 * (data['EngineTorque_Nm'] * data['EngineSpeed_rpm'] / 1000) / (2000 * 1500)
    noise = np.random.normal(0, 2, num_points)
    data['FuelRate_kg_h'] = np.clip(base_fuel_rate + fuel_rate_variation + noise, 0, 200)
    
    # Air Flow
    base_air_flow = 300
    air_flow_variation = 1000 * (data['EngineSpeed_rpm'] - 1200) / 600
    noise = np.random.normal(0, 20, num_points)
    data['AirFlow_kg_h'] = np.clip(base_air_flow + air_flow_variation + noise, 0, 2000)
    
    # Boost Pressure and Temperature
    data['BoostPressure_kPa'] = data['IntakePress_kPa'] + np.random.normal(0, 2, num_points)
    data['BoostTemp_C'] = data['IntakeTemp_C'] + 30 + np.random.normal(0, 3, num_points)
    
    # After-treatment Temperatures
    data['AfterTreatTemp1_C'] = data['ExhaustTemp_C'] - 50 + np.random.normal(0, 10, num_points)
    data['AfterTreatTemp2_C'] = data['AfterTreatTemp1_C'] - 30 + np.random.normal(0, 8, num_points)
    
    # DPF Pressure (low, gradual increase)
    data['DPF_Pressure_kPa'] = 5 + 10 * (time / duration) + np.random.normal(0, 1, num_points)
    
    # SCR Temperatures
    data['SCR_InletTemp_C'] = data['AfterTreatTemp2_C'] + np.random.normal(0, 5, num_points)
    data['SCR_OutletTemp_C'] = data['SCR_InletTemp_C'] - 20 + np.random.normal(0, 5, num_points)
    
    # DEF (Diesel Exhaust Fluid) System
    data['DEF_Pressure_bar'] = 6 + 2 * np.sin(2 * np.pi * time / 200) + np.random.normal(0, 0.2, num_points)
    data['DEF_Temp_C'] = 25 + 5 * (1 - np.exp(-time / 1000)) + np.random.normal(0, 0.5, num_points)
    
    # Emissions (NOx varies with load)
    base_nox = 800
    nox_variation = 600 * (data['EngineTorque_Nm'] - 1000) / 2000
    noise = np.random.normal(0, 50, num_points)
    data['NOx_Upstream_ppm'] = np.clip(base_nox + nox_variation + noise, 0, 2000)
    
    # NOx downstream (after SCR, much lower)
    conversion = 0.85 + 0.1 * np.random.random(num_points)
    data['NOx_Downstream_ppm'] = data['NOx_Upstream_ppm'] * (1 - conversion)
    data['NOx_Conversion_percent'] = conversion * 100
    
    # CO2
    data['CO2_percent'] = 8 + 4 * (data['FuelRate_kg_h'] / 120) + np.random.normal(0, 0.2, num_points)
    
    # CO
    data['CO_ppm'] = 150 + 200 * np.random.random(num_points)
    
    # HC (Hydrocarbons)
    data['HC_ppm'] = 20 + 40 * np.random.random(num_points)
    
    # PM (Particulate Matter)
    data['PM_mg_m3'] = 5 + 20 * np.random.random(num_points)
    
    # O2
    data['O2_percent'] = 12 - 6 * (data['FuelRate_kg_h'] / 120) + np.random.normal(0, 0.3, num_points)
    
    # Lambda ratio
    data['Lambda_ratio'] = 1.2 - 0.3 * (data['FuelRate_kg_h'] / 120) + np.random.normal(0, 0.02, num_points)
    
    # Environmental conditions
    data['AmbientTemp_C'] = 22 + 2 * np.sin(2 * np.pi * time / 1800) + np.random.normal(0, 0.5, num_points)
    data['AmbientPress_kPa'] = 101.3 + np.random.normal(0, 0.1, num_points)
    data['Humidity_percent'] = 55 + 10 * np.sin(2 * np.pi * time / 900) + np.random.normal(0, 2, num_points)
    
    # Electrical
    data['BatteryVoltage_V'] = 25.5 + 1.5 * np.sin(2 * np.pi * time / 100) + np.random.normal(0, 0.1, num_points)
    data['AlternatorCurrent_A'] = 80 + 60 * (data['EngineSpeed_rpm'] - 1200) / 600 + np.random.normal(0, 5, num_points)
    data['ECU_Temp_C'] = 50 + 20 * (1 - np.exp(-time / 600)) + np.random.normal(0, 1, num_points)
    
    # Transmission
    data['TransmissionOilTemp_C'] = 70 + 30 * (1 - np.exp(-time / 800)) + np.random.normal(0, 2, num_points)
    
    # Vehicle/Cab
    data['CabinTemp_C'] = 22 + np.random.normal(0, 0.5, num_points)
    
    # Vehicle dynamics (transient test)
    vehicle_speed = 40 + 30 * np.sin(2 * np.pi * time / 300) + 20 * np.sin(2 * np.pi * time / 150)
    data['VehicleSpeed_km_h'] = np.clip(vehicle_speed + np.random.normal(0, 2, num_points), 0, 120)
    
    # Throttle position (correlated with torque demand)
    throttle = 40 + 40 * (data['EngineTorque_Nm'] - 1000) / 2000
    data['ThrottlePosition_percent'] = np.clip(throttle + np.random.normal(0, 3, num_points), 0, 100)
    
    # Brake pressure (occasional braking)
    brake_events = np.random.random(num_points) < 0.05
    data['BrakePress_kPa'] = brake_events * (400 + 300 * np.random.random(num_points))
    
    # Clutch position (occasional shifts)
    clutch_events = np.random.random(num_points) < 0.03
    data['ClutchPosition_percent'] = clutch_events * (80 + 20 * np.random.random(num_points))
    
    # Add some intentional violations for testing
    # Introduce occasional coolant overtemp
    overheat_mask = (time > 1000) & (time < 1100)
    data['CoolantTemp_C'][overheat_mask] += 15
    
    # Introduce occasional NOx spike
    spike_mask = (time > 600) & (time < 650)
    data['NOx_Downstream_ppm'][spike_mask] *= 2
    
    # Introduce missing data
    missing_indices = np.random.choice(num_points, size=int(num_points * 0.001), replace=False)
    for sensor in ['OilPressure_kPa', 'FuelTemp_C']:
        if sensor in data:
            temp_array = np.array(data[sensor])
            temp_array[missing_indices] = np.nan
            data[sensor] = temp_array
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    return df


def generate_steady_state_test(duration=600, num_sensors=50):
    """
    Generate sample steady-state test data
    
    Parameters:
    - duration: Test duration in seconds (default 600)
    - num_sensors: Number of sensor columns to generate
    """
    
    # For steady state, use 1Hz sampling
    sample_rate = 1
    num_points = duration * sample_rate
    time = np.linspace(0, duration, num_points)
    
    data = {'Time': time}
    
    # Steady state - parameters should be relatively constant
    
    # Engine Speed (constant)
    data['EngineSpeed_rpm'] = 1500 + np.random.normal(0, 5, num_points)
    
    # Engine Torque (constant)
    data['EngineTorque_Nm'] = 2000 + np.random.normal(0, 10, num_points)
    
    # Temperatures (stable after warm-up)
    warmup_factor = 1 - np.exp(-time / 120)
    
    data['CoolantTemp_C'] = 70 + 25 * warmup_factor + np.random.normal(0, 0.5, num_points)
    data['OilTemp_C'] = 80 + 30 * warmup_factor + np.random.normal(0, 0.8, num_points)
    data['ExhaustTemp_C'] = 400 + 150 * warmup_factor + np.random.normal(0, 5, num_points)
    
    # Pressures (stable)
    data['OilPressure_kPa'] = 450 + np.random.normal(0, 3, num_points)
    data['IntakePress_kPa'] = 180 + np.random.normal(0, 2, num_points)
    data['ExhaustPress_kPa'] = 250 + np.random.normal(0, 3, num_points)
    data['FuelPressure_bar'] = 1400 + np.random.normal(0, 10, num_points)
    
    # Fuel and Air
    data['FuelRate_kg_h'] = 90 + np.random.normal(0, 1, num_points)
    data['AirFlow_kg_h'] = 1200 + np.random.normal(0, 10, num_points)
    
    # Emissions (stable)
    data['NOx_Upstream_ppm'] = 1200 + np.random.normal(0, 30, num_points)
    data['NOx_Downstream_ppm'] = 180 + np.random.normal(0, 10, num_points)
    data['CO2_percent'] = 10.5 + np.random.normal(0, 0.1, num_points)
    data['O2_percent'] = 8.5 + np.random.normal(0, 0.2, num_points)
    
    # Other parameters
    data['BatteryVoltage_V'] = 25.0 + np.random.normal(0, 0.05, num_points)
    data['AmbientTemp_C'] = 23 + np.random.normal(0, 0.2, num_points)
    data['AmbientPress_kPa'] = 101.3 + np.random.normal(0, 0.05, num_points)
    
    df = pd.DataFrame(data)
    
    return df


if __name__ == "__main__":
    print("PUMA Test Data Generator")
    print("=" * 50)
    
    # Generate Transient 1Hz test
    print("\nGenerating Transient 1Hz test (1800s)...")
    df_trans_1hz = generate_transient_test(frequency='1Hz', duration=1800)
    df_trans_1hz.to_excel('sample_transient_1hz.xlsx', index=False)
    print(f"✅ Generated: sample_transient_1hz.xlsx ({len(df_trans_1hz)} rows, {len(df_trans_1hz.columns)} columns)")
    
    # Generate Transient 10Hz test
    print("\nGenerating Transient 10Hz test (1800s)...")
    df_trans_10hz = generate_transient_test(frequency='10Hz', duration=1800)
    df_trans_10hz.to_excel('sample_transient_10hz.xlsx', index=False)
    print(f"✅ Generated: sample_transient_10hz.xlsx ({len(df_trans_10hz)} rows, {len(df_trans_10hz.columns)} columns)")
    
    # Generate Steady State test
    print("\nGenerating Steady State test (600s)...")
    df_steady = generate_steady_state_test(duration=600)
    df_steady.to_excel('sample_steady_state.xlsx', index=False)
    print(f"✅ Generated: sample_steady_state.xlsx ({len(df_steady)} rows, {len(df_steady.columns)} columns)")
    
    # Generate Baseline (slightly different values)
    print("\nGenerating Baseline test for comparison...")
    df_baseline = generate_transient_test(frequency='1Hz', duration=1800)
    # Offset values slightly
    for col in df_baseline.columns:
        if col != 'Time':
            df_baseline[col] = df_baseline[col] * 0.98 + np.random.normal(0, 0.5, len(df_baseline))
    df_baseline.to_excel('sample_baseline.xlsx', index=False)
    print(f"✅ Generated: sample_baseline.xlsx ({len(df_baseline)} rows, {len(df_baseline.columns)} columns)")
    
    print("\n" + "=" * 50)
    print("✅ All sample files generated successfully!")
    print("\nFiles created:")
    print("  - sample_transient_1hz.xlsx")
    print("  - sample_transient_10hz.xlsx")
    print("  - sample_steady_state.xlsx")
    print("  - sample_baseline.xlsx")
    print("\nUse these files with sample_config.csv for testing.")
