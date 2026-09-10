# AFM force-curve interpretation basics

An atomic force microscope records force as the probe approaches and retracts from a surface. AFM Explorer calls the approach branch the push series and the return branch the retract series.

## Contact point and stiffness

Before contact, a well-behaved approach curve usually has a relatively flat baseline dominated by noise and long-range interactions. The contact point marks the transition into the region where probe deflection changes systematically as displacement continues. AFM Explorer fits an approximately linear window after this transition. The fitted slope is used as a stiffness-related measurement; it should be compared only when calibration, probe, acquisition settings and analysis method are compatible.

The classical estimate is a sliding-window heuristic. The machine-learning estimate selects a candidate window using a model trained from human contact-point labels. An ML result is not automatically more accurate: held-out evaluation against trusted labels is needed.

## Maps and missing pixels

A scan may declare a complete rectangular grid even when the exported file contains only a subset of curves. Missing locations are not zero-valued measurements. They should remain missing, and curve navigation must use the available coordinate inventory.
