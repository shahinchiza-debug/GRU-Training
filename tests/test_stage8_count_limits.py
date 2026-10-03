import copy
import unittest

from app.stages.stage08_intents.run import (
    DEFAULT_CONFIG_PATH, allowed_counts, annotate_valid_stage8, load_json,
)


class CountLimitsTest(unittest.TestCase):
    def setUp(self):
        self.config = load_json(DEFAULT_CONFIG_PATH)
        self.template = {
            "template_id": "COUNT_TEST",
            **{p: {"state": p + ".1"} for p in ("P1", "P2", "P3", "P4", "P5")},
            "D_1": {"state": "D2@P3"}, "D_2": {"state": "D5@P5"},
            "stage7": {"final_turn_allocations": {
                "P1": 1, "P2": 4, "P3": 1, "P4": 1, "P5": 1,
                "D_slot_1": 1, "D_slot_2": 1,
            }},
        }

    def test_regular_cap(self):
        for turns in (1, 2, 3, 4, 8):
            self.assertEqual(
                allowed_counts([1, 2, 3, 4, 5], {"state": "P2.4", "turn_count": turns}, self.config),
                list(range(1, min(turns, 4) + 1)),
            )

    def test_exceptions_ignore_turns_but_keep_max_four(self):
        for state in ("P2.2", "P4.3", "D5"):
            self.assertEqual(allowed_counts(
                [1, 2, 3, 4, 5], {"state": state, "turn_count": 1}, self.config
            ), [1, 2, 3, 4])

    def test_end_to_end_state_counts_and_service_plan(self):
        for seed in range(30):
            t = copy.deepcopy(self.template)
            t["template_id"] = str(seed)
            t["P2"]["state"] = "P2.3"
            t["P4"]["state"] = "P4.3"
            t["stage7"]["final_turn_allocations"]["P2"] = 2
            valid, result = annotate_valid_stage8(t, self.config)
            self.assertTrue(valid)
            a = result["stage8"]["assignments"]
            self.assertEqual(a["P2"]["intent_count"], 2)
            self.assertEqual(a["P2"]["intent_count"], 1 + result["stage8"]["service_plan"]["P2"]["service_count"])
            self.assertEqual(a["D_1"]["target_count"], 1)
            for key in ("P4", "D_2"):
                self.assertLessEqual(a[key]["target_count"], a[key]["available_target_count"])
                self.assertIn(a[key]["target_count"], (2, 3))

    def test_p2_2_skips_turn_cap(self):
        t = copy.deepcopy(self.template)
        t["P2"]["state"] = "P2.2"
        t["stage7"]["final_turn_allocations"]["P2"] = 1
        valid, result = annotate_valid_stage8(t, self.config)
        self.assertTrue(valid)
        self.assertIn(result["stage8"]["assignments"]["P2"]["intent_count"], (2, 3, 4))

    def test_p2_3_and_p2_4_require_two_turns(self):
        for state in ("P2.3", "P2.4"):
            t = copy.deepcopy(self.template)
            t["P2"]["state"] = state
            t["stage7"]["final_turn_allocations"]["P2"] = 1
            valid, result = annotate_valid_stage8(t, self.config)
            self.assertFalse(valid)
            self.assertEqual(result["stage8"]["reason_code"], "INSUFFICIENT_STATE_TURNS")

    def test_no_state_count_fits(self):
        self.template["P2"]["state"] = "P2.4"
        self.template["stage7"]["final_turn_allocations"]["P2"] = 1
        valid, result = annotate_valid_stage8(self.template, self.config)
        self.assertFalse(valid)
        self.assertEqual(result["stage8"]["reason_code"], "INSUFFICIENT_STATE_TURNS")

    def test_p2_1_is_booking_only_and_fits_one_turn(self):
        self.template["stage7"]["final_turn_allocations"]["P2"] = 1
        valid, result = annotate_valid_stage8(self.template, self.config)
        self.assertTrue(valid)
        self.assertEqual(result["stage8"]["assignments"]["P2"]["intent_count"], 1)
        self.assertEqual(result["stage8"]["service_plan"]["P2"]["service_count"], 0)

    def test_fixed_counts_respect_turns(self):
        for key in ("P3", "D_slot_1"):
            t = copy.deepcopy(self.template)
            t["stage7"]["final_turn_allocations"][key] = 0
            self.assertFalse(annotate_valid_stage8(t, self.config)[0])
        self.template["D_1"]["state"] = "D3@P3"
        self.template["stage7"]["final_turn_allocations"]["D_slot_1"] = 0
        self.assertFalse(annotate_valid_stage8(self.template, self.config)[0])


if __name__ == "__main__":
    unittest.main()
