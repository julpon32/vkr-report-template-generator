# backend/app/ml_engine_simple.py
# ml_engine_simple.py

print("LOADED ml_engine_simple.py NEW VERSION")


from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
from .ml_dataset import TRAIN_SAMPLES

_classifier = None

def _build_pipeline():
    from sklearn.pipeline import Pipeline, FeatureUnion
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.svm import LinearSVC
    from sklearn.calibration import CalibratedClassifierCV

    word_vec = TfidfVectorizer(
        lowercase=True,
        analyzer="word",
        ngram_range=(1, 2),
        min_df=1,
    )
    char_vec = TfidfVectorizer(
        lowercase=True,
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=1,
    )

    feats = FeatureUnion([("word", word_vec), ("char", char_vec)], n_jobs=1)

    base = LinearSVC(class_weight="balanced")
    clf = CalibratedClassifierCV(base, method="sigmoid", cv=3)

    return Pipeline([("feats", feats), ("clf", clf)])


def get_classifier():
    global _classifier
    if _classifier is not None:
        return _classifier

    X = [t for (t, _) in TRAIN_SAMPLES]
    y = [lab for (_, lab) in TRAIN_SAMPLES]

    pipe = _build_pipeline()
    pipe.fit(X, y)
    _classifier = pipe
    return _classifier


def predict_labels(fragments: List[str]) -> List[Dict[str, Any]]:
    clf = get_classifier()
    if not fragments:
        return []

    labels = clf.predict(fragments)

    proba: Optional[List[List[float]]] = None
    if hasattr(clf, "predict_proba"):
        proba = clf.predict_proba(fragments)  # calibrated -> есть

    classes = list(getattr(clf, "classes_", []))

    out = []
    for i, frag in enumerate(fragments):
        lab = str(labels[i])
        score = 0.0
        if proba is not None and classes:
            try:
                idx = classes.index(lab)
                score = float(proba[i][idx])
            except Exception:
                score = 0.0

        out.append({"fragment": frag, "label": lab, "score": score})
    return out
