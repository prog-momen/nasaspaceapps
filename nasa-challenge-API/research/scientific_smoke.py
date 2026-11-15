"""Reproducible, bounded scientific smoke test; not the EarthTrend application."""
import sys,pathlib,json,time,platform,warnings,hashlib
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import numpy as np,pandas as pd,scipy,statsmodels,pymannkendall as mk
from scipy import stats
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.stats.diagnostic import acorr_ljungbox

t0=time.perf_counter()
raw=(ROOT/'test_power_monthly.raw').read_bytes();d=json.loads(raw)
vals=d['properties']['parameter']['T2M']; fill=d['header']['fill_value']
monthly={k:v for k,v in vals.items() if 1<=int(k[-2:])<=12}
s=pd.Series(monthly,dtype=float);s.index=pd.to_datetime(s.index,format='%Y%m');s=s.sort_index().asfreq('MS').replace(fill,np.nan)
assert len(s)==252 and s.notna().all() and s.index.is_unique
s.rename('T2M_C').to_csv(ROOT/'power_nablus_monthly_2005_2025.csv',index_label='month')
annual=s.groupby(s.index.year).apply(lambda x:np.average(x,weights=x.index.days_in_month))
sen=stats.theilslopes(annual.values,annual.index.values,alpha=.95)
mkres=mk.hamed_rao_modification_test(annual.values)
lr=stats.linregress(annual.index.values,annual.values)
def scores(actual,pred):
    err=np.asarray(actual)-np.asarray(pred)
    return {'MAE_C':float(np.abs(err).mean()),'RMSE_C':float(np.sqrt((err**2).mean()))}
def naive(train,h):return np.repeat(train.iloc[-1],h)
def snaive(train,h):return np.resize(train.iloc[-12:].to_numpy(),h)
def sarima(train,h):
    with warnings.catch_warnings(record=True) as warn:
        warnings.simplefilter('always')
        fit=SARIMAX(train,order=(1,0,0),seasonal_order=(1,0,0,12),trend='c',enforce_stationarity=True,enforce_invertibility=True).fit(disp=False,maxiter=100)
    forecast=fit.get_forecast(steps=h)
    return forecast.predicted_mean,fit,forecast,[str(w.message) for w in warn]
cv=[]
for n in [180,192,204,216]:
    train=s.iloc[:n];actual=s.iloc[n:n+12]
    pred,fit,fc,ww=sarima(train,12)
    cv.append({'train_end':str(train.index[-1].date()),'test_start':str(actual.index[0].date()),'test_end':str(actual.index[-1].date()),'naive':scores(actual,naive(train,12)),'seasonal_naive':scores(actual,snaive(train,12)),'sarima':scores(actual,pred),'converged':bool(fit.mle_retvals.get('converged')),'warnings':ww})
train=s.iloc[:228];actual=s.iloc[228:];pred,fit,fc,ww=sarima(train,24)
interval=fc.conf_int(alpha=.05)
cv_s=float(np.mean([r['sarima']['MAE_C'] for r in cv]));cv_b=float(np.mean([r['seasonal_naive']['MAE_C'] for r in cv]))
test_s=scores(actual,pred);test_b=scores(actual,snaive(train,24));accepted=cv_s<cv_b and test_s['MAE_C']<test_b['MAE_C'] and bool(fit.mle_retvals.get('converged'))
lb=acorr_ljungbox(fit.resid.iloc[24:],lags=[12,24],return_df=True)
result={
 'scope':'Small NASA POWER T2M grid-point smoke test; not a validated regional climate result or production forecast',
 'location':{'longitude':35.26,'latitude':32.22,'meaning':'POWER grid cell queried near Nablus; not a station measurement or Amazon LST'},
 'source_sha256':hashlib.sha256(raw).hexdigest(),'source_api':d['header']['api'],'source_time_standard':d['header']['time_standard'],
 'series':{'first':str(s.index[0].date()),'last':str(s.index[-1].date()),'monthly_count':len(s),'annual_summary_keys_removed':len(vals)-len(monthly),'missing':int(s.isna().sum()),'unit':'degC'},
 'descriptive':{'mean_C':float(s.mean()),'min_C':float(s.min()),'max_C':float(s.max())},
 'annual_trend_exploratory':{'annual_weighting':'days in month','n':len(annual),'ols_slope_C_per_year':float(lr.slope),'ols_p_iid_only':float(lr.pvalue),'sen_slope_C_per_year':float(sen.slope),'sen_95pct_iid_interval':[float(sen.low_slope),float(sen.high_slope)],'hamed_rao_p':float(mkres.p),'hamed_rao_tau':float(mkres.Tau),'lag1_residual_acf':float(pd.Series(lr.intercept+lr.slope*annual.index.values-annual.values).autocorr()),'warning':'21 annual points; exploratory sensitivity check. Theil-Sen analytic interval assumes suitable independence and is not a corrected autocorrelation interval.'},
 'forecast':{'candidate':'SARIMA(1,0,0)(1,0,0,12) with constant','candidate_selection':'Only one fixed SARIMA candidate; not exhaustive order optimization','rolling_expanding_cv':cv,'mean_cv_sarima_MAE_C':cv_s,'mean_cv_seasonal_naive_MAE_C':cv_b,'holdout_train_end':'2023-12-01','holdout_period':'2024-01 through 2025-12','holdout_sarima':test_s,'holdout_seasonal_naive':test_b,'holdout_naive':scores(actual,naive(train,24)),'nominal_interval':.95,'empirical_holdout_coverage':float(np.mean((actual.values>=interval.iloc[:,0].values)&(actual.values<=interval.iloc[:,1].values))),'ljung_box':lb.reset_index(names='lag').to_dict(orient='records'),'converged':bool(fit.mle_retvals.get('converged')),'warnings':ww,'eligible_under_smoke_gate':accepted,'production_reliability':'not established','future_forecast_published':False},
 'runtime':{'elapsed_seconds':round(time.perf_counter()-t0,3),'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'statsmodels':statsmodels.__version__,'pymannkendall':mk.__version__,'gpu_used':False,'peak_ram_measured':False},
}
(ROOT/'scientific_smoke_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
pd.DataFrame({'actual_C':actual,'predicted_C':pred,'lower_95_C':interval.iloc[:,0],'upper_95_C':interval.iloc[:,1],'seasonal_naive_C':snaive(train,24)}).to_csv(ROOT/'forecast_holdout_2024_2025.csv',index_label='month')
print(json.dumps(result,ensure_ascii=False,indent=2))
