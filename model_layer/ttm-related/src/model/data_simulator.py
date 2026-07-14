"""
Data Simulator - Generate fake OBD-II sensor data for testing
This creates simulated sensor readings that look like real car data
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


class OBDDataSimulator:
    """Generates simulated OBD-II sensor data"""

    def __init__(self, sequence_length=100, sampling_rate=1.0):
        """
        Args:
            sequence_length: Number of time steps (default: 100 seconds)
            sampling_rate: Samples per second (default: 1 Hz)
        """
        self.sequence_length = sequence_length
        self.sampling_rate = sampling_rate

    def generate_normal_sequence(self):
        """Generate normal driving pattern"""
        time = np.arange(0, self.sequence_length, 1 / self.sampling_rate)

        # RPM: varies between 800-3000 (idle to moderate driving)
        rpm = (
            1500 + 500 * np.sin(time / 10)
            + np.random.normal(0, 50, len(time))
        )
        rpm = np.clip(rpm, 800, 6000)

        # Coolant temp: starts at 20°C, warms up to 90°C, then stable
        coolant_temp = 20 + 70 * (1 - np.exp(-time / 30))
        coolant_temp += np.random.normal(0, 1, len(time))
        coolant_temp = np.clip(coolant_temp, 20, 95)

        # MAP: turbocharged Seat Leon 1.4 TSI — regularly exceeds
        # atmospheric pressure. KIT dataset: median 115.8 kPa,
        # P99 225 kPa, range 36–237 kPa.
        map_ = (
            100 + (rpm - 800) / 30
            + np.random.normal(0, 5, len(time))
        )
        map_ = np.clip(map_, 36, 237)

        # MAF: maintain maf/map ratio in the normal 0.1–0.3 band.
        # KIT dataset: MAF median 19.3 g/s, mean 23.3 g/s, max 122.7.
        maf = map_ * 0.2 + np.random.normal(0, 1, len(time))
        maf = np.clip(maf, 0, 123)

        # Throttle position (TPS): varies with RPM
        tps = (
            10 + (rpm - 800) / 50
            + np.random.normal(0, 5, len(time))
        )
        tps = np.clip(tps, 0, 100)

        # Speed: loosely derived from RPM.
        # KIT mean ~65 km/h at mean RPM ~1520.
        speed = np.clip(
            (rpm - 600) / 14 + np.random.normal(0, 5, len(time)),
            0, 218
        )

        # Accelerator pedal D and E: both track a common base signal
        # with small independent noise so they stay correlated ~0.97.
        # KIT dataset: both ~14 % at idle, up to ~85 % at high demand.
        pedal_base = np.clip(10 + (rpm - 800) / 100, 14, 85)
        accel_pedal_d = np.clip(
            pedal_base + np.random.normal(0, 1, len(time)), 0, 100
        )
        accel_pedal_e = np.clip(
            pedal_base + np.random.normal(0, 1, len(time)), 0, 100
        )

        return pd.DataFrame({
            'timestamp': [
                datetime.now() + timedelta(seconds=i) for i in time
            ],
            'rpm': rpm,
            'coolant_temp': coolant_temp,
            'map': map_,
            'maf': maf,
            'tps': tps,
            'speed': speed,
            'accel_pedal_d': accel_pedal_d,
            'accel_pedal_e': accel_pedal_e,
        })

    def generate_cooling_degradation(self):
        """Generate cooling system failure pattern"""
        df = self.generate_normal_sequence()

        # After warm-up, temperature keeps rising (water pump failure)
        time = np.arange(len(df))
        mask = df['coolant_temp'] > 85
        df.loc[mask, 'coolant_temp'] += (
            (time[mask] - time[mask].min()) * 0.05
        )
        df['coolant_temp'] = np.clip(df['coolant_temp'], 20, 110)

        return df

    def generate_air_intake_maf_anomaly(self, variant="low_maf"):
        """Generate air_intake_maf_anomaly patterns (INTERFACE.md enum).

        variant="low_maf" (was generate_intake_blockage):
            MAF reads 30% low for the given MAP — dirty air
            filter / MAF sensor drift. Story 7 `maf x 0.7`
            scenario.
        variant="map_bias" (was generate_vacuum_leak):
            MAP 30% high with throttle 30% low — vacuum-leak
            style plausibility fault.
        """
        df = self.generate_normal_sequence()

        if variant == "low_maf":
            # MAF is lower than expected for given MAP
            df['maf'] *= 0.7  # 30% lower MAF
        elif variant == "map_bias":
            # MAP is higher than normal while throttle is low
            df['map'] *= 1.3   # 30% higher MAP
            df['tps'] *= 0.7   # 30% lower throttle
        else:
            raise ValueError(f"Unknown variant: {variant}")

        return df

    def generate_pedal_sensor_fault(self):
        """Generate accelerator_pedal_sensor fault pattern.

        Injects sustained divergence (>10 pp) between pedal D and E
        after the first quarter of the sequence, simulating a
        dual-sensor disagreement fault.
        """
        df = self.generate_normal_sequence()

        fault_start = len(df) // 4
        df.loc[fault_start:, 'accel_pedal_e'] -= 15
        df['accel_pedal_e'] = np.clip(df['accel_pedal_e'], 0, 100)

        return df


# Test the simulator
if __name__ == "__main__":
    print("Testing OBD Data Simulator...")

    simulator = OBDDataSimulator(sequence_length=100)

    normal = simulator.generate_normal_sequence()
    cooling = simulator.generate_cooling_degradation()
    maf_low = simulator.generate_air_intake_maf_anomaly("low_maf")
    map_bias = simulator.generate_air_intake_maf_anomaly("map_bias")
    pedal = simulator.generate_pedal_sensor_fault()

    print("\nGenerated 5 sequences:")
    print(f"   - Normal: {len(normal)} samples")
    print(f"   - Cooling degradation: {len(cooling)} samples")
    print(f"   - MAF anomaly (low_maf): {len(maf_low)} samples")
    print(f"   - MAF anomaly (map_bias): {len(map_bias)} samples")
    print(f"   - Pedal sensor fault: {len(pedal)} samples")

    print("\nNormal sequence stats:")
    print(normal.describe())

    print("\nSimulator working correctly!")
