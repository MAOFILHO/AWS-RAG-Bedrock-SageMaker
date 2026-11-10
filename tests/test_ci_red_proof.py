"""Throwaway: QA proof for #83 AC3. A failing test must turn the CI check red. Never merge."""


def test_deliberately_fails_to_prove_ci_goes_red():
    assert 1 == 2, "deliberate failure for #83 AC3"
