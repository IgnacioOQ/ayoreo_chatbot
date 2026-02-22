"""Ayoreo POS tagset definition, mapped to Universal Dependencies."""

# Universal Dependencies POS tags used for Ayoreo
# See: https://universaldependencies.org/u/pos/
TAGSET = {
    "NOUN": "Noun",
    "VERB": "Verb",
    "ADJ": "Adjective",
    "ADV": "Adverb",
    "PRON": "Pronoun",
    "DET": "Determiner",
    "ADP": "Adposition (postposition in Ayoreo)",
    "CONJ": "Conjunction",
    "PART": "Particle",
    "INTJ": "Interjection",
    "NUM": "Numeral",
    "PROPN": "Proper noun",
    "PUNCT": "Punctuation",
    "X": "Unknown / unclassifiable",
}

# Ayoreo-specific morphological features to track
# These will be refined as grammar analysis progresses
MORPHOLOGICAL_FEATURES = {
    "person": ["1", "2", "3"],
    "number": ["Sing", "Plur"],
    "tense": ["Past", "Pres", "Fut"],
    "gender": ["Masc", "Fem"],  # If applicable in Ayoreo
}
