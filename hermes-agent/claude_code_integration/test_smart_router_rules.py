"""Unit tests for smart_router_rules model-tier + mode/effort recommendation.

Run with: python -m unittest test_smart_router_rules
from the claude_code_integration directory.

The TestClassifyPrompt / TestFormatSuggestion classes were deleted on
2026-09-23 with the skill-suggestion branch itself (see the module docstring
of smart_router_rules and docs/decisions/log.md).
"""

from __future__ import annotations

import unittest

from smart_router_rules import (
    recommend_mode_effort,
    recommend_model_tier,
)



class TestRecommendModelTier(unittest.TestCase):
    def assertTier(self, prompt: str, expected_model: str) -> None:
        tier = recommend_model_tier(prompt)
        self.assertIsNotNone(tier, f"Expected {expected_model}, got None for: {prompt!r}")
        assert tier is not None
        self.assertEqual(
            tier.model, expected_model,
            f"For prompt {prompt!r}: expected {expected_model}, got {tier.model}",
        )

    def test_optimal_algorithm_routes_to_fable(self) -> None:
        self.assertTier(
            "prove this algorithm is optimal from first principles", "fable"
        )

    def test_security_audit_routes_to_opus(self) -> None:
        self.assertTier("security audit of the new payments module", "opus")

    def test_rename_routes_to_haiku(self) -> None:
        self.assertTier("rename the helper variable in this file please", "haiku")

    def test_implement_feature_routes_to_sonnet(self) -> None:
        self.assertTier(
            "implement the session handler feature with unit tests", "sonnet"
        )

    def test_high_beats_impl_precedence(self) -> None:
        # HIGH (opus) patterns are checked before IMPL (sonnet).
        self.assertTier(
            "plan the architecture and then implement the new feature", "opus"
        )

    def test_slash_command_returns_none(self) -> None:
        self.assertIsNone(recommend_model_tier("/think plan this out end to end"))

    def test_short_prompt_returns_none(self) -> None:
        self.assertIsNone(recommend_model_tier("show status now"))

    def test_empty_returns_none(self) -> None:
        self.assertIsNone(recommend_model_tier(""))



class TestRecommendModeEffort(unittest.TestCase):
    def assertME(self, prompt, mode, effort, tier):
        me = recommend_mode_effort(prompt)
        self.assertIsNotNone(me, f"None for {prompt!r}")
        self.assertEqual((me.mode, me.effort, me.tier), (mode, effort, tier), prompt)

    def test_fable_algorithm_e5(self):
        self.assertME("prove this algorithm is optimal from first principles", "ALGORITHM", "E5", "fable")

    def test_opus_native_e4(self):
        self.assertME("security audit of the new payments module", "NATIVE", "E4", "opus")

    def test_sonnet_native_e3(self):
        self.assertME("implement the geo session handler feature end-to-end", "NATIVE", "E3", "sonnet")

    def test_haiku_minimal_e1(self):
        self.assertME("rename the helper variable in this file please", "MINIMAL", "E1", "haiku")

    def test_none_when_tier_none(self):
        self.assertIsNone(recommend_mode_effort("hi there how are you"))

    def test_slash_command_none(self):
        self.assertIsNone(recommend_mode_effort("/think plan this out end to end"))

    def test_consistency_with_tier(self):
        # mode/effort must never disagree with recommend_model_tier
        for p in ["prove this is optimal from first principles",
                  "how should we architect the new auth service",
                  "refactor the whole ingestion module for clarity",
                  "bump the version number in the setup file"]:
            t = recommend_model_tier(p); me = recommend_mode_effort(p)
            self.assertEqual(me.tier, t.model, p)


if __name__ == "__main__":
    unittest.main()
