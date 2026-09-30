"""
experiments/test_physical_consistency.py

Comprehensive physical consistency test suite verifying energy balance equations,
PID control, disturbance responses, cooling capacity saturation, and status transitions.
"""

import unittest
from backend.simulation_engine import SimulationEngine
from config import parameters as p


class TestPhysicalConsistency(unittest.TestCase):

    def setUp(self):
        self.engine = SimulationEngine()
        # Clear scheduled disturbance events for isolated unit test scenarios
        self.engine.door_disturbance.events = []

    def test_1_no_disturbance_pull_down(self):
        """TEST 1: Door closed, pull down from 25°C to -18°C setpoint."""
        self.engine.reset(t_initial_degc=25.0, t_setpoint_degc=-18.0, controller_type="pid")
        self.engine.door_disturbance.events = []
        
        # Run pull-down simulation for 12,000 seconds (200 minutes)
        for _ in range(12000):
            self.engine.step(dt_s=1.0)
            
        state = self.engine.get_current_state()
        final_temp = state["temperature_degc"]
        cooling_power = state["cooling_power_w"]
        
        # Temperature should reach and stabilize near setpoint (-18.0°C)
        self.assertAlmostEqual(final_temp, -18.0, delta=0.5, msg=f"Final temp {final_temp}°C not near setpoint -18°C")
        
        # Cooling power at steady-state should balance heat leak (344 W)
        self.assertAlmostEqual(cooling_power, p.Q_COOLING_MAX_W, delta=10.0)

    def test_2_short_door_opening(self):
        """TEST 2: Short door opening event and recovery."""
        self.engine.reset(t_initial_degc=-18.0, t_setpoint_degc=-18.0, controller_type="pid")
        self.engine.door_disturbance.events = []
        
        # Stable initial state
        self.engine.step(dt_s=1.0)
        t_before = self.engine.plant.temperature_degc
        
        # Open door for 30 seconds
        self.engine.set_door_state(True)
        for _ in range(30):
            state = self.engine.step(dt_s=1.0)
            # Energy balance: Q_in (2064 W) > Q_cooling (344 W) -> temp MUST rise
            self.assertGreater(state["q_in_w"], state["cooling_power_w"])
            self.assertGreaterEqual(state["dt_dt_degc_per_s"], -1e-6)
            
        t_open = self.engine.plant.temperature_degc
        self.assertGreater(t_open, t_before, msg="Temperature did not rise when door was open!")
        
        # Close door and recover for 5000 seconds (2 time constants tau=2500s)
        self.engine.set_door_state(False)
        for _ in range(5000):
            self.engine.step(dt_s=1.0)
            
        t_recovered = self.engine.plant.temperature_degc
        self.assertAlmostEqual(t_recovered, -18.0, delta=0.5, msg="Temperature failed to recover after door closed!")

    def test_3_long_door_opening_capacity_limit(self):
        """TEST 3: Long door opening leading to cooling capacity limit."""
        self.engine.reset(t_initial_degc=-18.0, t_setpoint_degc=-18.0, controller_type="pid")
        self.engine.door_disturbance.events = []
        
        self.engine.set_door_state(True)
        for _ in range(300):
            state = self.engine.step(dt_s=1.0)
            
        # Capacity limit verified: Q_in (~2000 W) > Q_cooling_max (344 W)
        self.assertGreater(state["q_in_w"], p.Q_COOLING_MAX_W)
        self.assertEqual(state["cooling_power_w"], p.Q_COOLING_MAX_W)
        self.assertIn("CAPACITY", state["intelligent_feature"]["display_title"].upper())

    def test_4_close_door_after_long_opening_recovery(self):
        """TEST 4: Close door after long opening -> RECOVERING -> NORMAL."""
        self.engine.reset(t_initial_degc=-18.0, t_setpoint_degc=-18.0, controller_type="pid")
        self.engine.door_disturbance.events = []
        
        # Long door open
        self.engine.set_door_state(True)
        for _ in range(120):
            self.engine.step(dt_s=1.0)
            
        # Close door
        self.engine.set_door_state(False)
        
        # Step 30 seconds after door close to allow exponential rate filter to reflect negative cooling derivative
        for _ in range(30):
            state = self.engine.step(dt_s=1.0)
            
        self.assertEqual(state["intelligent_feature"]["severity_level"], "RECOVERING")
        
        # Step until temp reaches setpoint (7500s = 3 time constants)
        for _ in range(7500):
            state = self.engine.step(dt_s=1.0)
            
        self.assertAlmostEqual(self.engine.plant.temperature_degc, -18.0, delta=0.5)
        self.assertEqual(state["intelligent_feature"]["severity_level"], "NORMAL")

    def test_5_excessive_thermal_load(self):
        """TEST 5: Q_in > Q_cooling_max -> 100% cooling, temp rises, no fake recovery."""
        self.engine.reset(t_initial_degc=-10.0, t_setpoint_degc=-18.0, t_ambient_degc=40.0, controller_type="pid")
        self.engine.door_disturbance.events = []
        self.engine.set_door_state(True)
        
        for _ in range(60):
            state = self.engine.step(dt_s=1.0)
            
        self.assertGreater(state["q_in_w"], state["cooling_power_w"])
        self.assertGreater(state["dt_dt_degc_per_s"], 0)
        self.assertNotEqual(state["intelligent_feature"]["severity_level"], "RECOVERING")

    def test_6_low_thermal_load(self):
        """TEST 6: Q_in < Q_cooling_max -> temp decreases towards setpoint."""
        self.engine.reset(t_initial_degc=-10.0, t_setpoint_degc=-18.0, t_ambient_degc=25.0, controller_type="pid")
        self.engine.door_disturbance.events = []
        
        for _ in range(100):
            state = self.engine.step(dt_s=1.0)
            
        self.assertLess(state["q_in_w"], state["cooling_power_w"])
        self.assertLess(state["dt_dt_degc_per_s"], 0)

    def test_7_setpoint_reached_stability(self):
        """TEST 7: T_actual ≈ T_set -> Cooling settles to balance heat load."""
        self.engine.reset(t_initial_degc=-18.0, t_setpoint_degc=-18.0, controller_type="pid")
        self.engine.door_disturbance.events = []
        
        for _ in range(200):
            state = self.engine.step(dt_s=1.0)
            
        self.assertAlmostEqual(state["temperature_degc"], -18.0, delta=0.1)
        self.assertAlmostEqual(state["q_in_w"], state["cooling_power_w"], delta=5.0)


if __name__ == "__main__":
    unittest.main()
