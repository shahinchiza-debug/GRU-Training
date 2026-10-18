import unittest

from app.stages.stage04_turns.run import allocate_counts
from app.stages.stage05_language.run import allocate_counts as allocate_language_counts


class Stage4DistributionTests(unittest.TestCase):
    def test_allocates_every_template_with_largest_remainder(self):
        allocations = [
            {"turn_count": 6, "percent": 20},
            {"turn_count": 8, "percent": 20},
            {"turn_count": 9, "percent": 10},
            {"turn_count": 10, "percent": 10},
            {"turn_count": 12, "percent": 10},
            {"turn_count": 14, "percent": 10},
            {"turn_count": 18, "percent": 10},
            {"turn_count": 25, "percent": 10},
        ]

        self.assertEqual(
            allocate_counts(224, allocations),
            [45, 45, 23, 23, 22, 22, 22, 22],
        )

    def test_zero_percent_bucket_stays_empty(self):
        allocations = [
            {"turn_count": 6, "percent": 0},
            {"turn_count": 8, "percent": 0},
            {"turn_count": 9, "percent": 100},
        ]

        self.assertEqual(allocate_counts(17, allocations), [0, 0, 17])

    def test_language_allocation_uses_configured_percentages(self):
        config = {
            "language_order": ["formal", "orten", "vardaglig", "brytande"],
            "languages": {
                "formal": {"percent": 10},
                "orten": {"percent": 30},
                "vardaglig": {"percent": 40},
                "brytande": {"percent": 20},
            },
        }

        self.assertEqual(
            allocate_language_counts(179, config),
            {"formal": 18, "orten": 54, "vardaglig": 71, "brytande": 36},
        )


if __name__ == "__main__":
    unittest.main()
