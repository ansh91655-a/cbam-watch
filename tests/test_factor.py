"""CBAM 계수 자료(data/factor.json)의 검사와 공개 모양."""
import copy
import unittest

from tools.common.jsonio import read_json
from tools.publish import factor


class FactorTest(unittest.TestCase):
    def setUp(self):
        self.body = read_json(factor.SOURCE, None)

    def test_the_stored_values_are_all_found_in_the_legal_texts(self):
        self.assertEqual(factor.problems(self.body), [])
        self.assertEqual([path["key"] for path in self.body["paths"]], ["current", "proposed"])

    def test_a_changed_value_is_reported_as_drift_from_the_text(self):
        body = copy.deepcopy(self.body)
        body["paths"][0]["values"]["2030"] = 52.5
        found = factor.problems(body)
        self.assertEqual([where for where, _ in found], ["경로 current 2030"])
        self.assertTrue(found[0][1].startswith("근거 어긋남"))

    def test_a_stated_phrase_must_be_in_the_text_and_carry_the_value(self):
        body = copy.deepcopy(self.body)
        body["paths"][1]["stated"]["2034"] = "20% from 2034 to 2037"
        self.assertTrue(any("글에 없는 대목" in what for _, what in factor.problems(body)))
        body = copy.deepcopy(self.body)
        body["paths"][1]["values"]["2035"] = 14
        self.assertTrue(any("값 14" in what for _, what in factor.problems(body)))

    def test_shape_problems_are_not_called_drift(self):
        body = copy.deepcopy(self.body)
        body["paths"][0]["values"]["2031"] = 60  # 앞의 해보다 커짐
        found = [what for _, what in factor.problems(body)]
        self.assertTrue(any("커짐" in what for what in found))
        self.assertEqual(factor.problems({"paths": []})[0][1], "자료(data/factor.json)를 읽지 못함")

    def test_the_public_shape_drops_repository_paths(self):
        public = factor.public(self.body)
        self.assertNotIn("path", public["paths"][0]["source"])
        self.assertNotIn("stated", public["paths"][0])
        self.assertEqual(public["paths"][1]["values"]["2038"], 0)


if __name__ == "__main__":
    unittest.main()
