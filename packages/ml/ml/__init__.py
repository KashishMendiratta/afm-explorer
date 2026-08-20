"""afm-ml: the AI component of the AFM Explorer project.

- dataset.py   turns hand-labeled curves into a windowed training set
- train.py     trains the supervised contact-point classifier (GBM) and the
               unsupervised curve-quality model (IsolationForest)
- infer.py     scores a new curve with a trained model, mirroring the
               classical heuristic's FitResult interface
- evaluate.py  benchmarks the trained model against the classical
               afm_core.heuristics baseline on held-out labeled curves
"""
