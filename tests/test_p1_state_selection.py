import sys
import unittest
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = WORKSPACE_ROOT / "app"
sys.path.insert(0, str(APP_ROOT))

from stages.stage01_raw.run import DEFAULT_STRUCTURE_PATH, generate_raw_templates, load_json


class P1StateSelectionTests(unittest.TestCase):
    def test_only_p1_1_and_p1_3_are_generated(self):
        structure = load_json(DEFAULT_STRUCTURE_PATH)

        p1_states = [item["state_id"] for item in structure["p_space"]["categories"]["p1"]]
        self.assertEqual(p1_states, ["P1.1", "P1.3"])

        p_combinations, d_configs = generate_raw_templates(structure)
        self.assertEqual({item["p1"]["state_id"] for item in p_combinations}, {"P1.1", "P1.3"})
        self.assertEqual(len(p_combinations), 144)
        self.assertEqual(len(d_configs), 157)
        self.assertEqual(len(p_combinations) * len(d_configs), 22608)


if __name__ == "__main__":
    unittest.main()
