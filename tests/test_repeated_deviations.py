import unittest

from app.stages.stage10_hierarchy.run import deviation_node_ids


class RepeatedDeviationsTest(unittest.TestCase):
    def test_repeated_type_gets_unique_node_ids(self):
        deviations = [("D_1", "D1", "P3"), ("D_2", "D1", "P5")]
        self.assertEqual(
            deviation_node_ids(deviations),
            {"D_1": "D1_1", "D_2": "D1_2"},
        )

    def test_different_types_keep_simple_node_ids(self):
        deviations = [("D_1", "D1", "P3"), ("D_2", "D3", "P5")]
        self.assertEqual(
            deviation_node_ids(deviations),
            {"D_1": "D1", "D_2": "D3"},
        )


if __name__ == "__main__":
    unittest.main()
