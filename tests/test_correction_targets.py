import random
import unittest

from app.stages.stage09_pools.run import build_corrections, resolve_target_count
from app.stages.stage10_hierarchy.run import validate_correction_targets


def template(state, targets):
    return {
        "flow": ["P2", state],
        "nodes": {
            "P2": {"state": "P2.1", "intents": [
                {"intent_id": "BOOK_001", "mlp1": "Booking", "mlp2": "boka"},
                {
                    "intent_id": "SVC_001",
                    "mlp1": "Tjänster",
                    "mlp2": "lägga till",
                    "parameters": {"service": "fade"},
                },
            ]},
            state: {"state": state, "target_count": len(targets), "targets": targets},
        },
    }


class CorrectionTargetsTest(unittest.TestCase):
    def test_d2_can_change_three_fields_in_one_object(self):
        validate_correction_targets(template("D2", [{
            "target_id": "BOOK_001", "mlp1": "Booking", "mlp2": "omboka",
            "parameters": {"day": "fredag", "time": "12:00", "staff": "Sara"},
        }]))

    def test_d5_accepts_booking_and_service(self):
        validate_correction_targets(template("D5", [
            {"target_id": "BOOK_001", "mlp1": "Booking", "mlp2": "omboka"},
            {
                "target_id": "SVC_001",
                "mlp1": "Tjänster",
                "mlp2": "byta ut",
                "parameters": {"service": "styling"},
            },
        ]))

    def test_d5_rejects_repeated_target(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_correction_targets(template("D5", [
                {"target_id": "BOOK_001"}, {"target_id": "BOOK_001"},
            ]))

    def test_counts_enforced(self):
        for state, ids in [("D2", ["BOOK_001", "SVC_001"]), ("D5", ["BOOK_001"])]:
            with self.subTest(state=state), self.assertRaises(ValueError):
                validate_correction_targets(template(state, [{"target_id": i} for i in ids]))
        for state, count in [("D2", 2), ("D5", 1)]:
            with self.subTest(state=state), self.assertRaises(ValueError):
                build_corrections(state, count, [], random.Random(1), {}, {})

    def test_future_target_rejected(self):
        with self.assertRaisesRegex(ValueError, "not active"):
            validate_correction_targets(template("D2", [{"target_id": "SVC_002"}]))

    def test_target_requires_matching_mlp1(self):
        with self.assertRaisesRegex(ValueError, "must use MLP1 Tjänster"):
            validate_correction_targets(template("D2", [{
                "target_id": "SVC_001",
                "mlp1": "Booking",
                "mlp2": "omboka",
            }]))

    def test_remove_and_cancel_are_not_supported_in_v1(self):
        for mlp1, mlp2 in [
            ("Tjänster", "ta bort"),
            ("Booking", "avboka"),
        ]:
            with self.subTest(mlp2=mlp2), self.assertRaisesRegex(ValueError, "unsupported"):
                validate_correction_targets(template("D2", [{
                    "target_id": "SVC_001" if mlp1 == "Tjänster" else "BOOK_001",
                    "mlp1": mlp1,
                    "mlp2": mlp2,
                }]))

    def test_booking_change_is_supported_in_v1(self):
        validate_correction_targets(template("D2", [{
            "target_id": "BOOK_001",
            "mlp1": "Booking",
            "mlp2": "ändra",
            "parameters": {"staff": "Sara"},
        }]))

    def test_changed_target_can_be_used_in_later_block(self):
        value = template("D2", [{
            "target_id": "SVC_001",
            "mlp1": "Tjänster",
            "mlp2": "byta ut",
            "parameters": {"service": "styling"},
        }])
        value["flow"].append("P4")
        value["nodes"]["P4"] = {
            "state": "P4.2", "target_count": 1,
            "targets": [{
                "target_id": "SVC_001",
                "mlp1": "Tjänster",
                "mlp2": "byta ut",
                "parameters": {"service": "tvätt"},
            }],
        }
        validate_correction_targets(value)

    def test_insufficient_targets_do_not_get_repeated(self):
        self.assertIsNone(build_corrections(
            "D5", 2, ["SVC_001", "SVC_001"], random.Random(1), {}, {}
        ))
        result = build_corrections(
            "D5", 2, ["SVC_001", "SVC_002"], random.Random(1),
            {"service_pool": ["fade", "slingor", "styling", "tvätt"]}, {},
            {"SVC_001": "fade", "SVC_002": "slingor"},
        )
        self.assertEqual(len({item["target_id"] for item in result}), 2)

    def test_multiple_service_replacements_reserve_distinct_services(self):
        result = build_corrections(
            "D5", 2, ["SVC_001", "SVC_002"], random.Random(1),
            {"service_pool": ["fade", "slingor", "styling", "tvätt"]}, {},
            {"SVC_001": "fade", "SVC_002": "slingor"},
        )
        replacements = [item["parameters"]["service"] for item in result]
        self.assertEqual(len(replacements), len(set(replacements)))

    def test_duplicate_replacement_service_is_rejected(self):
        value = {
            "flow": ["P2", "D5"],
            "nodes": {
                "P2": {"state": "P2.2", "intents": [
                    {"intent_id": "BOOK_001", "mlp1": "Booking", "mlp2": "boka"},
                    {"intent_id": "SVC_001", "mlp1": "Tjänster", "mlp2": "lägga till", "parameters": {"service": "fade"}},
                    {"intent_id": "SVC_002", "mlp1": "Tjänster", "mlp2": "lägga till", "parameters": {"service": "slingor"}},
                ]},
                "D5": {"state": "D5", "target_count": 2, "targets": [
                    {"target_id": "SVC_001", "mlp1": "Tjänster", "mlp2": "byta ut", "parameters": {"service": "styling"}},
                    {"target_id": "SVC_002", "mlp1": "Tjänster", "mlp2": "byta ut", "parameters": {"service": "styling"}},
                ]},
            },
        }
        with self.assertRaisesRegex(ValueError, "duplicate active service"):
            validate_correction_targets(value)

    def test_replacement_respects_exclusive_service_group(self):
        value = {
            "flow": ["P2", "D2"],
            "nodes": {
                "P2": {"state": "P2.2", "intents": [
                    {"intent_id": "BOOK_001", "mlp1": "Booking", "mlp2": "boka"},
                    {"intent_id": "SVC_001", "mlp1": "Tjänster", "mlp2": "lägga till", "parameters": {"service": "fade"}},
                    {"intent_id": "SVC_002", "mlp1": "Tjänster", "mlp2": "lägga till", "parameters": {"service": "styling"}},
                ]},
                "D2": {"state": "D2", "target_count": 1, "targets": [{
                    "target_id": "SVC_002", "mlp1": "Tjänster", "mlp2": "byta ut",
                    "parameters": {"service": "herrklippning"},
                }]},
            },
        }
        with self.assertRaisesRegex(ValueError, "exclusive service group"):
            validate_correction_targets(value)

    def test_replacement_respects_incompatible_service_pair(self):
        value = {
            "flow": ["P2", "D2"],
            "nodes": {
                "P2": {"state": "P2.2", "intents": [
                    {"intent_id": "BOOK_001", "mlp1": "Booking", "mlp2": "boka"},
                    {"intent_id": "SVC_001", "mlp1": "Tjänster", "mlp2": "lägga till", "parameters": {"service": "skäggtrimning"}},
                    {"intent_id": "SVC_002", "mlp1": "Tjänster", "mlp2": "lägga till", "parameters": {"service": "styling"}},
                ]},
                "D2": {"state": "D2", "target_count": 1, "targets": [{
                    "target_id": "SVC_002", "mlp1": "Tjänster", "mlp2": "byta ut",
                    "parameters": {"service": "damklippning"},
                }]},
            },
        }
        with self.assertRaisesRegex(ValueError, "incompatible service pair"):
            validate_correction_targets(value)

    def test_target_count_is_never_reduced_to_available_capacity(self):
        self.assertIsNone(resolve_target_count("P4.3", 4, ["BOOK_001", "AUTH_001"]))
        self.assertIsNone(resolve_target_count("D5", 3, ["BOOK_001", "SVC_001"]))
        self.assertEqual(resolve_target_count("D2", 1, ["BOOK_001"]), 1)
        self.assertIsNone(resolve_target_count("P4.3", 2, ["BOOK_001"]))


if __name__ == "__main__":
    unittest.main()
