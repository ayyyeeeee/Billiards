"""Penalized Student-t location/scale regression, with genuine censor likelihood.

This is a descriptive robust model, not an outlier deletion algorithm. Defaults
are prespecified (nu=5, mean basis dimension 5, log-scale dimension 3, second
difference penalty 1); they are not selected to maximize an experimental effect.
The t scale is NOT its SD: variance = scale**2 * nu/(nu-2).

Censor codes: -1 means latent Y <= recorded boundary, +1 means Y >= boundary,
0 means an exact observation. Caller must establish actual censoring from source
metadata; extreme values and statistical outlier flags are not censoring evidence.
Sources: scipy.stats.t (logpdf/logcdf/logsf), scipy.optimize.minimize L-BFGS-B.
"""
from dataclasses import dataclass, field
import numpy as np
from scipy.interpolate import BSpline
from scipy.optimize import minimize
from scipy.stats import t


def observation_loglik(y, mean, scale, censor, nu=5):
    """One log likelihood per observation, in original measurement units."""
    y, mean, scale, censor = np.broadcast_arrays(y, mean, scale, censor)
    if nu <= 2 or np.any(scale <= 0) or not np.isin(censor, [-1, 0, 1]).all():
        raise ValueError('Require nu>2, positive scale, censor in {-1,0,1}.')
    z = (y - mean) / scale
    return np.where(censor < 0, t.logcdf(z, nu),
                    np.where(censor > 0, t.logsf(z, nu),
                             t.logpdf(z, nu) - np.log(scale)))


def _basis(x, dimension, lo, hi):
    if dimension == 1:
        return np.ones((len(x), 1))
    degree = min(3, dimension - 1)
    inner = np.linspace(lo, hi, dimension - degree + 1)[1:-1]
    knots = np.r_[np.repeat(lo, degree + 1), inner,
                  np.repeat(hi, degree + 1)]
    return BSpline(knots, np.eye(dimension), degree, extrapolate=False)(x)


@dataclass
class FitResult:
    success: bool = False
    message: str = ''
    n_obs: int = 0
    n_censored: int = 0
    nu: float = 5.
    penalty: float = 1.
    used_mask: np.ndarray = field(default_factory=lambda: np.array([], dtype=bool))
    df_mean: int = 1
    df_scale: int = 1
    xmin: float = 0.
    xmax: float = 1.
    center: float = 0.
    unit: float = 1.
    coefficients: np.ndarray = field(default_factory=lambda: np.array([]))
    log_likelihood: float = np.nan
    tail_probability: np.ndarray = field(default_factory=lambda: np.array([]))
    weights: np.ndarray = field(default_factory=lambda: np.array([]))

    def predict(self, x):
        if not self.success:
            raise ValueError('Fit unavailable: ' + self.message)
        x = np.atleast_1d(np.asarray(x, dtype=float))
        if not np.isfinite(x).all():
            raise ValueError('Prediction coordinates must be finite.')
        if max(self.df_mean, self.df_scale) > 1 and (np.any(x < self.xmin) or np.any(x > self.xmax)):
            raise ValueError('Spline predictions must stay within observed range.')
        b = self.coefficients[:self.df_mean]
        g = self.coefficients[self.df_mean:]
        mean = self.center + self.unit * (_basis(x, self.df_mean, self.xmin, self.xmax) @ b)
        scale = self.unit * np.exp(_basis(x, self.df_scale, self.xmin, self.xmax) @ g)
        variance = scale**2 * self.nu / (self.nu - 2)
        return dict(mean=mean, scale=scale, variance=variance, sd=np.sqrt(variance))


def fit_student_t(x, y, censor=None, df_mean=5, df_scale=3, nu=5., penalty=1.):
    """Fit all valid observations without hard rejection; failure is explicit.

    Nonfinite x/y are missing, not zero. Too few observations, constant responses,
    all-censored samples, or numerical failures return success=False. No fallback
    OLS curve is silently substituted. Parameters are in robust standardized units.
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.ndim != 1 or y.shape != x.shape:
        raise ValueError('x and y must be equal-length one-dimensional arrays.')
    c = np.zeros(len(y), dtype=int) if censor is None else np.asarray(censor)
    if c.shape != y.shape or not np.isin(c, [-1, 0, 1]).all():
        raise ValueError('censor must match y and use only -1, 0, 1.')
    if nu <= 2 or penalty < 0 or min(df_mean, df_scale) < 1:
        raise ValueError('Require nu>2, nonnegative penalty and positive dimensions.')
    used = np.isfinite(x) & np.isfinite(y)
    x, y, c = x[used], y[used], c[used]
    out = FitResult(n_obs=len(y), n_censored=int(np.count_nonzero(c)), nu=nu,
                    penalty=penalty, used_mask=used, df_mean=df_mean, df_scale=df_scale)
    if len(y) < max(5, df_mean + df_scale + 2):
        out.message = 'Insufficient observations for requested location/scale model.'
        return out
    if np.count_nonzero(c == 0) < 3:
        out.message = 'At least three exact measurements required for identification.'
        return out
    if max(df_mean, df_scale) > 1 and len(np.unique(x)) < max(df_mean, df_scale):
        out.message = 'Too few distinct x values for spline basis.'
        return out
    out.xmin, out.xmax = float(x.min()), float(x.max())
    out.center = float(np.median(y))
    out.unit = float(np.median(np.abs(y - out.center)) / 0.67448975)
    if out.unit <= 1e-12 and np.any(c != 0):
        # More than half the sample can share a censor boundary. Its zero MAD
        # does not imply zero latent variance; normalize from exact observations.
        exact = y[c == 0]
        out.unit = float(np.std(exact, ddof=1))
    if out.unit <= 1e-12:
        out.message = 'Degenerate response scale; no reliable variance fit.'
        return out
    z = (y - out.center) / out.unit
    B = _basis(x, df_mean, out.xmin, out.xmax)
    S = _basis(x, df_scale, out.xmin, out.xmax)
    Dm = np.diff(np.eye(df_mean), n=2, axis=0)
    Ds = np.diff(np.eye(df_scale), n=2, axis=0)

    def objective(theta):
        beta, gamma = theta[:df_mean], theta[df_mean:]
        mu, logs = B @ beta, S @ gamma
        scales = np.exp(logs)
        r = (z - mu) / scales
        ll = observation_loglik(z, mu, scales, c, nu)
        # Derivatives of negative log likelihood with respect to mu and logs.
        gmu = -(nu + 1) * r / (nu + r*r) / scales
        glogs = 1 - (nu + 1) * r*r / (nu + r*r)
        left, right = c < 0, c > 0
        for mask, sign, logprob in ((left, 1., t.logcdf), (right, -1., t.logsf)):
            if mask.any():
                ratio = np.exp(t.logpdf(r[mask], nu) - logprob(r[mask], nu))
                gmu[mask] = sign * ratio / scales[mask]
                glogs[mask] = sign * ratio * r[mask]
        roughness = np.sum((Dm @ beta)**2) + np.sum((Ds @ gamma)**2)
        gradient = np.r_[B.T @ gmu + 2*penalty*Dm.T @ (Dm @ beta),
                         S.T @ glogs + 2*penalty*Ds.T @ (Ds @ gamma)]
        return -np.sum(ll) + penalty*roughness, gradient

    # Robust constant start avoids initializing a spline to one extreme trial.
    initial = np.r_[np.zeros(df_mean), np.zeros(df_scale)]
    result = minimize(objective, initial, jac=True, method='L-BFGS-B',
                      bounds=[(None, None)]*df_mean + [(-7., 7.)]*df_scale,
                      options={'maxiter': 1500, 'ftol': 1e-10, 'gtol': 1e-6})
    out.message = str(result.message)
    if not result.success or not np.isfinite(result.fun):
        return out
    if np.any(np.abs(result.x[df_mean:]) > 6.99):
        out.message = 'Scale reached numerical boundary; fit not accepted.'
        return out
    out.coefficients = result.x
    out.success = True
    pred = out.predict(x)
    out.log_likelihood = float(observation_loglik(y, pred['mean'], pred['scale'], c, nu).sum())
    residual = (y - pred['mean']) / pred['scale']
    # Descriptive model-tail probabilities, not externally calibrated p-values.
    out.tail_probability = np.where(c == 0, 2*t.sf(np.abs(residual), nu), np.nan)
    out.weights = np.where(c == 0, (nu + 1)/(nu + residual**2), np.nan)
    return out
