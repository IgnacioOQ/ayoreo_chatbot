"""Tests for the inference module."""

from src.inference.translator import build_translation_prompt
from src.pos_tagging.rule_engine import tokenize, RuleBasedTagger


def test_build_translation_prompt_ayo_to_en():
    examples = [
        {"ayoreo": "Ore ajnai.", "english": "We walk."},
    ]
    prompt = build_translation_prompt(
        "Ore ajnai guejna.",
        examples=examples,
        dict_entries=[],
        direction="ayo_to_en",
    )
    assert "Ayoreo" in prompt
    assert "English" in prompt
    assert "Ore ajnai." in prompt


def test_build_translation_prompt_en_to_ayo():
    examples = [
        {"ayoreo": "Ore ajnai.", "english": "We walk."},
    ]
    prompt = build_translation_prompt(
        "We walk well.",
        examples=examples,
        dict_entries=[],
        direction="en_to_ayo",
    )
    assert "English" in prompt
    assert "We walk." in prompt


def test_tokenize():
    tokens = tokenize("Dupade ome yoqui.")
    assert tokens == ["Dupade", "ome", "yoqui", "."]


def test_rule_based_tagger_dictionary():
    tagger = RuleBasedTagger(dictionary={"dupade": "PROPN", "ome": "VERB"})
    result = tagger.tag(["Dupade", "ome"])
    assert result == [("Dupade", "PROPN"), ("ome", "VERB")]


def test_rule_based_tagger_fallback():
    tagger = RuleBasedTagger()
    result = tagger.tag(["unknownword"])
    assert result == [("unknownword", "X")]
