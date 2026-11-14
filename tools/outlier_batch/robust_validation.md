# Robust model validation

{
  "fits": 40,
  "successful": 40,
  "holdout": {
    "interleaved": {
      "successful_folds": 200,
      "n": 5400,
      "t_nll_per_observation": 1.0536083777941352,
      "gaussian_nll_per_observation": 1.4127674574375375,
      "t_better_folds": 113
    },
    "blocked": {
      "successful_folds": 199,
      "n": 5372,
      "t_nll_per_observation": 1.1015734570037383,
      "gaussian_nll_per_observation": 1.5039532790897583,
      "t_better_folds": 139
    }
  }
}

Read-only evaluation of 40 trained channels. No source values changed. Full results and sensitivity grids are in robust_validation.json.

The comparator uses the same five-dimensional mean spline and Gaussian constant-scale likelihood, including the same censor mechanism. Without censoring it is the OLS spline/ML scale fit. The t model additionally allows varying scale and a smoothing penalty, so predictive gains cannot be attributed solely to t tails.

Holdouts are interpolation checks with endpoints retained; neither is a prospective forecasting test. Their folds and trials are dependent. NLL is evaluated in native units with censor probabilities; compare models on the same observations, not raw angle versus strength NLL. No significance or treatment-effect claim follows.

nu=5 and penalty=1 remain prespecified descriptive defaults; the 4/5/8 and .3/1/3 grid is a sensitivity check, not tuning. Variance can change under these assumptions, particularly with heavy censoring or small n. Smoothness does not mean residual noise was eliminated.
