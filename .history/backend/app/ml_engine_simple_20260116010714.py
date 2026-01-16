# backend/app/ml_engine_simple.py

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional

from .ml_dataset import TRAIN_SAMPLES


_classifier = None


def _build_sklearn_pipeline():
    """
    TF-IDF (word + char n-grams) + LogisticRegression.
    """
    from sklearn.pipeline import Pipeline, FeatureUnion
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

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

    feats = FeatureUnion(
        transformer_list=[
            ("word", word_vec),
            ("char", char_vec),
        ],
        n_jobs=1,
    )

    clf = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        n_jobs=1,
    )

    return Pipeline([("feats", feats), ("clf", clf)])


def get_classifier():
    """
    Ленивая инициализация.
    Возвращает обученный sklearn pipeline.
    """
    global _classifier
    if _classifier is not None:
        return _classifier

    # Готовим X, y
    X = [t for (t, _) in TRAIN_SAMPLES]
    y = [lab for (_, lab) in TRAIN_SAMPLES]

    try:
        pipe = _build_sklearn_pipeline()
        pipe.fit(X, y)
        _classifier = pipe
        return _classifier
    except Exception as e:
        raise RuntimeError(
            "ML модель не смогла инициализироваться. "
            "Проверь, что установлен scikit-learn: `python3 -m pip install -U scikit-learn`. "
            f"Текст ошибки: {e}"
        )


def predict_labels(fragments: List[str]) -> List[Dict[str, Any]]:
    """
    Возвращает label + score (вероятность/уверенность).
    Для LogisticRegression это predict_proba по предсказанному классу.
    """
    clf = get_classifier()

    if not fragments:
        return []

    # sklearn: predict + predict_proba
    labels = clf.predict(fragments)

    proba: Optional[List[List[float]]] = None
    if hasattr(clf, "predict_proba"):
        proba = clf.predict_proba(fragments)  # type: ignore

    out = []
    classes = list(getattr(clf, "classes_", []))

    for i, frag in enumerate(fragments):
        lab = str(labels[i])
        score = 0.0

        if proba is not None and classes:
            try:
                cls_idx = classes.index(lab)
                score = float(proba[i][cls_idx])
            except Exception:
                score = 0.0

        out.append({"fragment": frag, "label": lab, "score": score})

    return out