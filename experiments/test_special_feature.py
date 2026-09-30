"""
experiments/test_special_feature.py

Comprehensive Test Suite for Special Feature:
Intelligent Door Heat-Exchange Detection and Automatic Cooling Response.

Tests all 6 required engineering test scenarios.
"""

import unittest
from special_feature.intelligent_heat_assistant import IntelligentHeatAssistant


class TestIntelligentHeatAssistant(unittest.TestCase):

    def setUp(self):
        self.assistant = IntelligentHeatAssistant()

    def test_scenario_1_door_closed_normally(self):
        """Test 1: Door closed normally -> NORMAL state, no alarm."""
        res = self.assistant.process_step(
            inside_temp_degc=-18.0,
            ambient_temp_degc=25.0,
            setpoint_degc=-18.0,
            door_is_open=False,
            current_cooling_power_w=64.0,
            dt_s=1.0,
            sim_time_s=100.0,
        )

        self.assertEqual(res["severity_level"], "NORMAL")
        self.assertFalse(res["should_play_sound"])
        self.assertEqual(res["compensation_w"], 0.0)
        print("[OK] Test 1 Passed: Door closed normally -> NORMAL state.")

    def test_scenario_2_door_opened_briefly(self):
        """Test 2: Door opened briefly (5s) -> WARNING/LOW disturbance, no critical alarm."""
        for t in range(1, 6):
            res = self.assistant.process_step(
                inside_temp_degc=-17.8,
                ambient_temp_degc=25.0,
                setpoint_degc=-18.0,
                door_is_open=True,
                current_cooling_power_w=100.0,
                dt_s=1.0,
                sim_time_s=100.0 + t,
            )

        self.assertEqual(res["severity_level"], "WARNING")
        self.assertNotEqual(res["severity_level"], "CRITICAL")
        self.assertGreater(res["compensation_w"], 0.0)
        print("[OK] Test 2 Passed: Door opened briefly -> Moderate warning, non-critical.")

    def test_scenario_3_door_remains_open(self):
        """Test 3: Door remains open (30s) -> Thermal load increases, cooling power increases."""
        for t in range(1, 31):
            res = self.assistant.process_step(
                inside_temp_degc=-17.0 + (t * 0.05),
                ambient_temp_degc=25.0,
                setpoint_degc=-18.0,
                door_is_open=True,
                current_cooling_power_w=150.0,
                dt_s=1.0,
                sim_time_s=100.0 + t,
            )

        self.assertIn(res["severity_level"], ["WARNING", "CRITICAL"])
        self.assertGreater(res["compensation_w"], 50.0)
        print("[OK] Test 3 Passed: Door remains open -> Thermal load & cooling power increased.")

    def test_scenario_4_prolonged_door_open(self):
        """Test 4: Door remains open long time (120s) -> CRITICAL state & repeated alarm."""
        for t in range(1, 121):
            res = self.assistant.process_step(
                inside_temp_degc=-15.0 + (t * 0.08),
                ambient_temp_degc=25.0,
                setpoint_degc=-18.0,
                door_is_open=True,
                current_cooling_power_w=200.0,
                dt_s=1.0,
                sim_time_s=100.0 + t,
            )

        self.assertEqual(res["severity_level"], "CRITICAL")
        self.assertTrue(res["should_play_sound"])
        self.assertEqual(res["audio_pattern"], "REPEATED_ALARM")
        print("[OK] Test 4 Passed: Prolonged door open -> CRITICAL state & audio alarm triggered.")

    def test_scenario_5_door_close_recovery(self):
        """Test 5: Door closes after critical -> RECOVERING state, then NORMAL after temperature stabilizes."""
        # 1. Drive into critical
        for t in range(1, 60):
            self.assistant.process_step(
                inside_temp_degc=-12.0,
                ambient_temp_degc=25.0,
                setpoint_degc=-18.0,
                door_is_open=True,
                current_cooling_power_w=344.0,
                dt_s=1.0,
                sim_time_s=float(t),
            )

        # 2. Close door (should enter RECOVERING)
        res_rec = self.assistant.process_step(
            inside_temp_degc=-13.0,
            ambient_temp_degc=25.0,
            setpoint_degc=-18.0,
            door_is_open=False,
            current_cooling_power_w=344.0,
            dt_s=1.0,
            sim_time_s=61.0,
        )
        self.assertEqual(res_rec["severity_level"], "RECOVERING")

        # 3. Simulate temperature returning to setpoint
        for t in range(62, 300):
            temp = max(-18.0, -13.0 - ((t - 61) * 0.05))
            res_stable = self.assistant.process_step(
                inside_temp_degc=temp,
                ambient_temp_degc=25.0,
                setpoint_degc=-18.0,
                door_is_open=False,
                current_cooling_power_w=100.0,
                dt_s=1.0,
                sim_time_s=float(t),
            )

        self.assertEqual(res_stable["severity_level"], "NORMAL")
        print("[OK] Test 5 Passed: Door close -> RECOVERING -> NORMAL after temperature stabilizes.")

    def test_scenario_6_high_ambient_open_door(self):
        """Test 6: High ambient temp (40 degC) + open door -> More severe thermal disturbance."""
        for t in range(1, 30):
            res_high_amb = self.assistant.process_step(
                inside_temp_degc=-10.0 + (t * 0.1),
                ambient_temp_degc=40.0,
                setpoint_degc=-18.0,
                door_is_open=True,
                current_cooling_power_w=344.0,
                dt_s=1.0,
                sim_time_s=float(t),
            )

        self.assertEqual(res_high_amb["severity_level"], "CRITICAL")
        self.assertGreater(res_high_amb["estimated_heat_exchange_w"], 800.0)
        print("[OK] Test 6 Passed: High ambient temp + open door -> Severe thermal disturbance.")


if __name__ == "__main__":
    unittest.main()
