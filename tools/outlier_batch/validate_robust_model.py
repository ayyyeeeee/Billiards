"""Reproducible read-only actual-data model checks. Writes only validation JSON/MD."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm
from robust_model import fit_student_t, observation_loglik, _basis
from censoring import censor_codes, censor_values
from outlier_batch import find_training_csvs, build_eligibility_mask


def gaussian_fit_predict(x, y, c, test_x):
    """Same mean basis, constant Gaussian scale; handles censor likelihood fairly.

    With no censoring this is the OLS spline / ML residual scale comparator.
    """
    lo, hi = x.min(), x.max()
    B = _basis(x, 5, lo, hi)
    center, unit = np.median(y), np.std(y)
    z = (y-center)/unit
    beta = np.linalg.lstsq(B, z, rcond=None)[0]
    initial = np.r_[beta, np.log(max(np.std(z-B@beta), .01))]
    def nll(theta):
        r = (z-B@theta[:5])/np.exp(theta[5])
        return -np.where(c<0, norm.logcdf(r), np.where(c>0, norm.logsf(r), norm.logpdf(r)-theta[5])).sum()
    result = minimize(nll, initial, method='L-BFGS-B', bounds=[(None,None)]*5+[(-7,7)])
    if not result.success:
        return None
    return (center+unit*(_basis(test_x,5,lo,hi)@result.x[:5]), np.exp(result.x[5])*unit)


def main():
    records=[]
    for pid in [f'{i:02d}' for i in range(1,31)]:
        for path in find_training_csvs(pid):
            df=pd.read_csv(path)
            for channel in ('angle','strength'):
                valid=(df[channel+'_status'].eq('scored') & pd.to_numeric(df[channel+'_valid'],errors='coerce').eq(1) & np.isfinite(pd.to_numeric(df[channel+'_value'],errors='coerce'))).to_numpy(bool)
                if not valid.any(): continue
                x=df.loc[valid,'shot'].to_numpy(float)
                y=censor_values(df,channel)[valid]
                c=censor_codes(df,channel)[valid]
                base=fit_student_t(x,y,c)
                record=dict(participant=pid,channel=channel,n=len(y),censored=int(np.count_nonzero(c)),
                            success=base.success,message=base.message,sensitivity=[],holdout=[])
                if base.success:
                    pred=base.predict(x)
                    residual=(y-pred['mean'])/pred['scale']
                    adjacent=(np.diff(x)==1)&(c[:-1]==0)&(c[1:]==0)
                    record['adjacent_exact_residual_correlation']=float(np.corrcoef(residual[:-1][adjacent],residual[1:][adjacent])[0,1]) if adjacent.sum()>3 else None
                    for nu in (4.,5.,8.):
                        for penalty in (.3,1.,3.):
                            fit=fit_student_t(x,y,c,nu=nu,penalty=penalty)
                            s=dict(nu=nu,penalty=penalty,success=fit.success)
                            if fit.success:
                                alt=fit.predict(x)
                                s['mean_rms_change_in_default_sd']=float(np.sqrt(np.mean(((alt['mean']-pred['mean'])/pred['sd'])**2)))
                                s['median_variance_ratio']=float(np.median(alt['variance']/pred['variance']))
                            record['sensitivity'].append(s)
                    # Hold out interior points only, keeping endpoints for interpolation.
                    # Both interleaved and contiguous-block folds; no future forecasting claim.
                    interior=np.arange(1,len(x)-1)
                    for strategy in ('interleaved','blocked'):
                        folds=[interior[i::5] for i in range(5)] if strategy=='interleaved' else np.array_split(interior,5)
                        for fold,test in enumerate(folds):
                            train=np.ones(len(x),dtype=bool); train[test]=False
                            fit=fit_student_t(x[train],y[train],c[train])
                            gaussian=gaussian_fit_predict(x[train],y[train],c[train],x[test])
                            rec=dict(strategy=strategy,fold=fold,n=len(test),success=fit.success and gaussian is not None)
                            if rec['success']:
                                p=fit.predict(x[test]); gm,gs=gaussian
                                tz=observation_loglik(y[test],p['mean'],p['scale'],c[test],fit.nu)
                                gz=(y[test]-gm)/gs
                                gl=np.where(c[test]<0,norm.logcdf(gz),np.where(c[test]>0,norm.logsf(gz),norm.logpdf(gz)-np.log(gs)))
                                rec.update(t_nll=float(-tz.sum()),gaussian_nll=float(-gl.sum()))
                            record['holdout'].append(rec)
                records.append(record)
    summary=dict(fits=len(records),successful=sum(r['success'] for r in records),holdout={})
    for strategy in ('interleaved','blocked'):
        folds=[f for r in records for f in r['holdout'] if f['strategy']==strategy and f['success']]
        n=sum(f['n'] for f in folds)
        summary['holdout'][strategy]=dict(successful_folds=len(folds),n=n,t_nll_per_observation=sum(f['t_nll'] for f in folds)/n,
            gaussian_nll_per_observation=sum(f['gaussian_nll'] for f in folds)/n,
            t_better_folds=sum(f['t_nll']<f['gaussian_nll'] for f in folds))
    out=Path(__file__).parent
    (out/'robust_validation.json').write_text(json.dumps(dict(summary=summary,channels=records),indent=2,allow_nan=False),encoding='utf-8')
    text='# Robust model validation\n\n'+json.dumps(summary,indent=2)+'\n\n'
    text+='Read-only evaluation of 40 trained channels. No source values changed. Full results and sensitivity grids are in robust_validation.json.\n\n'
    text+='The comparator uses the same five-dimensional mean spline and Gaussian constant-scale likelihood, including the same censor mechanism. Without censoring it is the OLS spline/ML scale fit. The t model additionally allows varying scale and a smoothing penalty, so predictive gains cannot be attributed solely to t tails.\n\n'
    text+='Holdouts are interpolation checks with endpoints retained; neither is a prospective forecasting test. Their folds and trials are dependent. NLL is evaluated in native units with censor probabilities; compare models on the same observations, not raw angle versus strength NLL. No significance or treatment-effect claim follows.\n\n'
    text+='nu=5 and penalty=1 remain prespecified descriptive defaults; the 4/5/8 and .3/1/3 grid is a sensitivity check, not tuning. Variance can change under these assumptions, particularly with heavy censoring or small n. Smoothness does not mean residual noise was eliminated.\n'
    (out/'robust_validation.md').write_text(text,encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
