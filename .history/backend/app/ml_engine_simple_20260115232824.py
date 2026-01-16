# backend/app/ml_engine_simple.py

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

from .ml_dataset import TRAIN_SAMPLES


def _tokenize(text: str) -> List[str]:
    t = text.lower()
    t = t.replace("ё", "е")
    # оставляем буквы/цифры, режем на токены
    tokens = re.findall(r"[a-zа-я0-9]+", t)
    return tokens


class NaiveBayesTextClassifier:
    """
    Очень простой Multinomial Naive Bayes:
    P(class | text) ~ P(class) * Π P(token | class)
    """

    def __init__(self) -> None:
        self.class_counts = Counter()
        self.token_counts_by_class: Dict[str, Counter] = defaultdict(Counter)
        self.total_tokens_by_class = Counter()
        self.vocab = set()

    def fit(self, samples: List[Tuple[str, str]]) -> None:
        for text, label in samples:
            self.class_counts[label] += 1
            tokens = _tokenize(text)
            for tok in tokens:
                self.vocab.add(tok)
                self.token_counts_by_class[label][tok] += 1
                self.total_tokens_by_class[label] += 1

    def predict_proba_one(self, text: str) -> Dict[str, float]:
        tokens = _tokenize(text)
        vocab_size = max(1, len(self.vocab))
        total_docs = sum(self.class_counts.values())

        # лог-вероятности, чтобы не было underflow
        log_probs: Dict[str, float] = {}
        for cls, cls_cnt in self.class_counts.items():
            log_p = math.log(cls_cnt / total_docs)

            total_tok = self.total_tokens_by_class[cls]
            tok_counts = self.token_counts_by_class[cls]

            for tok in tokens:
                # Laplace smoothing
                p_tok = (tok_counts[tok] + 1) / (total_tok + vocab_size)
                log_p += math.log(p_tok)

            log_probs[cls] = log_p

        # softmax
        max_log = max(log_probs.values())
        exps = {k: math.exp(v - max_log) for k, v in log_probs.items()}
        s = sum(exps.values())
        return {k: (v / s) for k, v in exps.items()}

    def predict_one(self, text: str) -> Tuple[str, float]:
        probs = self.predict_proba_one(text)
        label = max(probs, key=probs.get)
        return label, float(probs[label])


_classifier = None


def get_classifier() -> NaiveBayesTextClassifier:
    global _classifier
    if _classifier is None:
        clf = NaiveBayesTextClassifier()
        clf.fit(TRAIN_SAMPLES)
        _classifier = clf
    return _classifier


def predict_labels(fragments: List[str]) -> List[Dict[str, Any]]:
    clf = get_classifier()
    out = []
    for frag in fragments:
        label, score = clf.predict_one(frag)
        out.append({"fragment": frag, "label": label, "score": score})
    return out
