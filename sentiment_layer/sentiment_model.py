from typing import Any, Dict


POSITIVE_WORDS = {
    "gain",
    "gains",
    "growth",
    "improve",
    "improved",
    "positive",
    "profit",
    "profits",
    "rally",
    "record",
    "recover",
    "recovery",
    "rise",
    "rises",
    "strong",
    "surge",
    "up",
}

NEGATIVE_WORDS = {
    "decline",
    "declines",
    "down",
    "drop",
    "fall",
    "falls",
    "loss",
    "losses",
    "negative",
    "pressure",
    "risk",
    "sell",
    "selling",
    "slump",
    "uncertain",
    "uncertainty",
    "weak",
}


def _label_from_score(score: float) -> str:
    if score > 0.05:
        return "Positive"
    if score < -0.05:
        return "Negative"
    return "Neutral"


class SimpleSentimentModel:
    """Week 2 sentiment baseline with optional VADER/TextBlob backends."""

    def __init__(self):
        self.backend = "rule_based"
        self._vader = None

        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

            self._vader = SentimentIntensityAnalyzer()
            self.backend = "vader"
        except Exception:
            self._vader = None

        if self._vader is None:
            try:
                from textblob import TextBlob  # noqa: F401

                self.backend = "textblob"
            except Exception:
                self.backend = "rule_based"

    def _analyze_with_vader(self, text: str) -> Dict[str, Any]:
        scores = self._vader.polarity_scores(text)
        score = round(float(scores.get("compound", 0.0)), 4)
        return {
            "label": _label_from_score(score),
            "score": score,
            "confidence": round(abs(score), 4),
            "raw_scores": scores,
            "backend": self.backend,
        }

    def _analyze_with_textblob(self, text: str) -> Dict[str, Any]:
        from textblob import TextBlob

        score = round(float(TextBlob(text).sentiment.polarity), 4)
        return {
            "label": _label_from_score(score),
            "score": score,
            "confidence": round(abs(score), 4),
            "raw_scores": {"polarity": score},
            "backend": self.backend,
        }

    def _analyze_with_rules(self, text: str) -> Dict[str, Any]:
        tokens = [
            token.strip(".,;:!?()[]{}'\"").lower()
            for token in text.split()
        ]
        positive_count = sum(1 for token in tokens if token in POSITIVE_WORDS)
        negative_count = sum(1 for token in tokens if token in NEGATIVE_WORDS)
        total = positive_count + negative_count

        if total == 0:
            score = 0.0
        else:
            score = (positive_count - negative_count) / total

        score = round(max(-1.0, min(1.0, score)), 4)
        return {
            "label": _label_from_score(score),
            "score": score,
            "confidence": round(abs(score), 4),
            "raw_scores": {
                "positive_terms": positive_count,
                "negative_terms": negative_count,
            },
            "backend": self.backend,
        }

    def analyze_text(self, text: str) -> Dict[str, Any]:
        text = str(text or "").strip()
        if not text:
            return {
                "label": "Neutral",
                "score": 0.0,
                "confidence": 0.0,
                "raw_scores": {},
                "backend": self.backend,
            }

        if self._vader is not None:
            return self._analyze_with_vader(text)

        if self.backend == "textblob":
            return self._analyze_with_textblob(text)

        return self._analyze_with_rules(text)


# Backward-compatible name for existing agent imports.
FinBERTSentimentModel = SimpleSentimentModel
