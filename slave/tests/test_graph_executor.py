"""Tests for output extraction keyword matching in graph_executor."""

from app.graph_executor import (
    _keyword_match,
    extract_outputs_from_text,
    extract_outputs_legacy,
)


# ── _keyword_match helper ────────────────────────────────────────────────────


class TestKeywordMatch:
    def test_exact_match(self):
        assert _keyword_match("YES", "The answer is YES") is True

    def test_false_positive_substring(self):
        assert _keyword_match("YES", "YESTERDAY was great") is False

    def test_false_positive_suffix(self):
        assert _keyword_match("NO", "NOTICE this") is False

    def test_case_insensitive(self):
        assert _keyword_match("yes", "The answer is Yes") is True

    def test_with_punctuation(self):
        assert _keyword_match("YES", "Is it YES?") is True
        assert _keyword_match("YES", "(YES)") is True

    def test_special_regex_chars_safe(self):
        """re.escape prevents keywords with regex chars from breaking."""
        # "C++" contains regex special chars but doesn't raise an error
        assert _keyword_match("C++", "I love C++ programming") is False  # \b can't match around non-word chars
        assert _keyword_match("yes!", "The answer is yes!") is False  # same reason

    def test_no_match(self):
        assert _keyword_match("YES", "The answer is NO") is False

    def test_multi_word(self):
        assert _keyword_match("NOT SURE", "I am NOT SURE about this") is True


# ── extract_outputs_from_text ────────────────────────────────────────────────


class TestExtractOutputsFromText:
    def test_keyword_exact_match(self):
        outputs = [{"name": "decision", "values": ["yes", "no"]}]
        result = extract_outputs_from_text("The answer is YES.", outputs)
        assert result == {"decision": "yes"}

    def test_keyword_no_false_positive(self):
        outputs = [{"name": "decision", "values": ["yes", "no"]}]
        result = extract_outputs_from_text("YESTERDAY I said NOTHING.", outputs)
        assert result == {"decision": None}

    def test_first_match_wins(self):
        outputs = [{"name": "decision", "values": ["yes", "no"]}]
        result = extract_outputs_from_text("YES and NO are both here.", outputs)
        assert result == {"decision": "yes"}

    def test_no_values_stores_full_text(self):
        outputs = [{"name": "summary", "values": []}]
        text = "Here is the full response."
        result = extract_outputs_from_text(text, outputs)
        assert result == {"summary": text}

    def test_empty_name_skipped(self):
        outputs = [{"name": "", "values": ["yes"]}]
        result = extract_outputs_from_text("YES", outputs)
        assert result == {}

    def test_multiple_outputs(self):
        outputs = [
            {"name": "approved", "values": ["yes", "no"]},
            {"name": "priority", "values": ["high", "low"]},
        ]
        result = extract_outputs_from_text("YES, this is HIGH priority.", outputs)
        assert result == {"approved": "yes", "priority": "high"}


# ── extract_outputs_legacy ───────────────────────────────────────────────────


class TestExtractOutputsLegacy:
    def test_keyword_exact_match(self):
        rules = {"decision": "keyword:yes|no"}
        result = extract_outputs_legacy("The answer is YES.", rules)
        assert result == {"decision": "yes"}

    def test_keyword_no_false_positive(self):
        rules = {"decision": "keyword:yes|no"}
        result = extract_outputs_legacy("YESTERDAY I said NOTHING.", rules)
        assert result == {"decision": None}

    def test_regex_still_works(self):
        rules = {"version": r"regex:v\d+\.\d+"}
        result = extract_outputs_legacy("Released v1.2 today.", rules)
        assert result == {"version": "v1.2"}

    def test_unknown_rule(self):
        rules = {"field": "unknown:value"}
        result = extract_outputs_legacy("some text", rules)
        assert result == {"field": None}
