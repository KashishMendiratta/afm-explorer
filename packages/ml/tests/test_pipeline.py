import numpy as np
from ml.dataset import build_window_dataset
from ml.evaluate import evaluate_baseline_vs_ml, split_labels_by_curve
from ml.infer import estimate, qc_score
from ml.train import train_contact_point_model, train_qc_model


def test_build_window_dataset_has_both_classes(synthetic_scan_and_labels):
    scan_caches, labels = synthetic_scan_and_labels
    dataset = build_window_dataset(scan_caches, labels)
    assert dataset.X.shape[0] == dataset.y.shape[0] == dataset.groups.shape[0]
    assert set(np.unique(dataset.y)) == {0, 1}
    assert dataset.X.shape[1] == len(dataset.feature_names)


def test_train_and_infer_roundtrip(synthetic_scan_and_labels):
    scan_caches, labels = synthetic_scan_and_labels
    train_labels, eval_labels = split_labels_by_curve(labels, test_frac=0.3, seed=1)

    dataset = build_window_dataset(scan_caches, train_labels)
    model = train_contact_point_model(dataset)

    assert 0.0 <= model.metrics["window_f1"] <= 1.0
    assert model.metrics["n_labeled_curves"] == len(train_labels)

    # sanity: the model should score reasonably on training-distribution
    # data — beat a coin flip on F1 given the clean synthetic separation
    assert model.metrics["window_f1"] > 0.5

    cache = scan_caches["synthetic-scan"]
    curve = next(iter(cache.curves.values()))
    fit = estimate(curve.distance, curve.force, model)
    assert fit.method == "ml"
    assert 0 <= fit.start_index < fit.end_index <= len(curve.distance)


def test_evaluate_baseline_vs_ml_report(synthetic_scan_and_labels):
    scan_caches, labels = synthetic_scan_and_labels
    train_labels, eval_labels = split_labels_by_curve(labels, test_frac=0.3, seed=2)

    dataset = build_window_dataset(scan_caches, train_labels)
    model = train_contact_point_model(dataset)

    report = evaluate_baseline_vs_ml(scan_caches, eval_labels, model)
    assert report.n_curves == len(eval_labels)
    assert report.heuristic_mean_abs_error is not None
    assert report.ml_mean_abs_error is not None
    # both errors should be well within the curve length, i.e. not garbage
    assert report.ml_mean_abs_error < 300
    assert report.heuristic_mean_abs_error < 300


def test_qc_model_flags_noisy_curve_more_than_clean_curve(synthetic_scan_and_labels):
    scan_caches, _ = synthetic_scan_and_labels
    qc_model = train_qc_model(scan_caches)

    cache = scan_caches["synthetic-scan"]
    clean_curve = next(iter(cache.curves.values()))
    noisy_d = clean_curve.distance
    rng = np.random.default_rng(42)
    noisy_f = clean_curve.force + rng.normal(0, 5.0, len(clean_curve.force))  # inject heavy noise

    clean_score = qc_score(clean_curve.distance, clean_curve.force, qc_model)
    noisy_score = qc_score(noisy_d, noisy_f, qc_model)
    assert noisy_score > clean_score
