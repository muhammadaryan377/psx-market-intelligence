from typing import Dict, List, Any
from transformers import pipeline


MODEL_NAME = "ProsusAI/finbert"


class FinBERTSentimentModel:
    """
    FinBERT financial sentiment model.
    Output labels:
    positive, negative, neutral
    """

    def __init__(self):
        print("Loading FinBERT sentiment model...")
        self.classifier = pipeline(
            task="text-classification",
            model=MODEL_NAME,
            tokenizer=MODEL_NAME,
            top_k=None,
            device=-1,  # CPU. If GPU available, use device=0
        )

    def _normalize_scores(self, raw_output: Any) -> List[Dict[str, float]]:
        """
        Handles different transformers output formats.
        """
        if isinstance(raw_output, list) and raw_output and isinstance(raw_output[0], list):
            raw_output = raw_output[0]

        normalized = []

        for item in raw_output:
            label = str(item.get("label", "")).lower()
            score = float(item.get("score", 0.0))

            normalized.append({
                "label": label,
                "score": score
            })

        return normalized

    def analyze_text(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                "label": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "raw_scores": []
            }

        # FinBERT/BERT max input limit hoti hai, is liye text trim kar rahe hain.
        text = text.strip()
        text = text[:3000]

        raw_output = self.classifier(
            text,
            truncation=True,
            max_length=512
        )

        scores = self._normalize_scores(raw_output)

        if not scores:
            return {
                "label": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "raw_scores": []
            }

        best = max(scores, key=lambda x: x["score"])
        label = best["label"]
        confidence = round(best["score"], 4)

        # Signed score:
        # positive = +confidence
        # negative = -confidence
        # neutral = 0
        if label == "positive":
            signed_score = confidence
        elif label == "negative":
            signed_score = -confidence
        else:
            signed_score = 0.0

        return {
            "label": label,
            "score": signed_score,
            "confidence": confidence,
            "raw_scores": scores
        }