# import pytensor  # needed for pymc
import pymc as pm
import arviz as az
import numpy as np
# import scipy as sp
import pandas as pd
# import seaborn as sns
# import pytensor.tensor as pt
# import matplotlib.pyplot as plt
# from scipy.special import gamma

# plotting parameters
# plt.rcParams.update({"font.size": 16})
# plt.rcParams.update({"figure.titlesize": 20})
# plt.rcParams["font.family"] = "DeJavu Serif"
# plt.rcParams["font.serif"] = "Cambria Math"


def get_model_comparisons(information_criteria: str):

    np.random.seed(27)

    df = pd.read_csv("./Italy_Mpox.csv")

    priors = pd.read_csv("./NE_posteriors.csv")
    priors = priors.rename(columns={"Unnamed: 0": "p"})
    ps_l = priors[priors.model == "LogNormal"]
    ps_l.reset_index(inplace=True, drop=True)
    ps_g = priors[priors.model == "Gamma"]
    ps_g.reset_index(inplace=True, drop=True)
    ps_w = priors[priors.model == "Weibull"]
    ps_w.reset_index(inplace=True, drop=True)
    ps_n = priors[priors.model == "NegativeBinomial"]
    ps_n.reset_index(inplace=True, drop=True)

    # N = len(df)
    tStartExposure = df["start"].values.astype("int")
    tEndExposure = df["end"].values.astype("int")
    tSymptomOnset = df["onset"].values.astype("int")

    obs = tSymptomOnset - tStartExposure

    # Lognormal model
    with pm.Model() as mod_l:
        r = pm.Beta("r", mu=ps_l["mean"][0], sigma=ps_l["sd"][0])  # exposure period increase rate (i.e. ranges between 0 and 1)
        e = pm.Deterministic("e", r * (tEndExposure - tStartExposure))  # exposure period effect
        a = pm.Gamma("a", mu=ps_l["mean"][1], sigma=ps_l["sd"][1])
        m = pm.Deterministic("m", a + e)  # location paramter
        s = pm.Gamma("s", mu=ps_l["mean"][2], sigma=ps_l["sd"][2])  # standard deviation parameter
        y = pm.LogNormal("y", mu=m, sigma=s, observed=obs)  # likelihood
        # ppc_l = pm.sample_prior_predictive(1000, random_seed=27)  # prior predictives

    # Gamma model
    with pm.Model() as mod_g:
        r = pm.Beta("r", mu=ps_g["mean"][0], sigma=ps_g["sd"][0])  # exposure period increase rate (i.e. ranges between 0 and 1)
        e = pm.Deterministic("e", r * (tEndExposure - tStartExposure))  # exposure period effect
        a = pm.Gamma("a", mu=ps_g["mean"][1], sigma=ps_g["sd"][1])
        m = pm.Deterministic("m", a + e)  # mean paramter
        s = pm.Gamma("s", mu=ps_g["mean"][2], sigma=ps_g["sd"][2])  # standard deviation parameter
        y = pm.Gamma("y", mu=m, sigma=s, observed=obs)
        # ppc_g = pm.sample_prior_predictive(1000, random_seed=27)  # prior predictives

    # Weibull model
    with pm.Model() as mod_w:
        r = pm.Beta("r", mu=ps_w["mean"][0], sigma=ps_w["sd"][0])  # exposure period increase rate (i.e. ranges between 0 and 1)
        e = pm.Deterministic("e", r * (tEndExposure - tStartExposure))  # exposure period effect
        a = pm.Gamma("a", mu=ps_w["mean"][1], sigma=ps_w["sd"][1])
        m = pm.Deterministic("m", a + e)  # shape paramter
        s = pm.Gamma("s", mu=ps_w["mean"][2], sigma=ps_w["sd"][2])  # scale parameter
        y = pm.Weibull("y", alpha=m, beta=s, observed=obs)
        # ppc_w = pm.sample_prior_predictive(1000, random_seed=27)  # prior predictives

    # Negative binomial model
    with pm.Model() as mod_n:
        r = pm.Beta("r", mu=ps_n["mean"][0], sigma=ps_n["sd"][0])  # exposure period increase rate (i.e. ranges between 0 and 1)
        e = pm.Deterministic("e", r * (tEndExposure - tStartExposure))  # exposure period effect
        a = pm.Gamma("a", mu=ps_n["mean"][1], sigma=ps_n["sd"][1])
        m = pm.Deterministic("m", a + e)  # location paramter
        s = pm.Gamma("s", mu=ps_n["mean"][2], sigma=ps_n["sd"][2])  # shape parameter
        y = pm.NegativeBinomial("y", mu=m, alpha=s, observed=obs)
        # ppc_n = pm.sample_prior_predictive(1000, random_seed=27)  # prior predictives

    # Sample models
    with mod_l:
        # idata_l = pm.sample(1000, idata_kwargs={"log_likelihood": True}, target_accept=0.99, random_seed=27)  # NUTS sampler
        idata_l = pm.sample(100, idata_kwargs={"log_likelihood": True}, target_accept=0.99, random_seed=27)  # NUTS sampler

    with mod_g:
        # idata_g = pm.sample(1000, idata_kwargs={"log_likelihood": True}, random_seed=27)  # NUTS sampler
        idata_g = pm.sample(100, idata_kwargs={"log_likelihood": True}, random_seed=27)  # NUTS sampler

    with mod_w:
        # idata_w = pm.sample(1000, idata_kwargs={"log_likelihood": True}, target_accept=0.99, random_seed=27)  # NUTS sampler
        idata_w = pm.sample(100, idata_kwargs={"log_likelihood": True}, target_accept=0.99, random_seed=27)  # NUTS sampler

    with mod_n:
        # idata_n = pm.sample(1000, idata_kwargs={"log_likelihood": True}, random_seed=27)  # NUTS sampler
        idata_n = pm.sample(100, idata_kwargs={"log_likelihood": True}, random_seed=27)  # NUTS sampler

    mods = {"LN": idata_l, "Gamma": idata_g, "Weibull": idata_w, "NB": idata_n}
    df = az.compare(mods, ic=information_criteria)
    print(f"df before: {df}")
    # df.rename(columns={"": "label"}, inplace=True)
    # df.columns.values[0] = "label"
    df.index.name = "label"
    df.reset_index(inplace=True)
    print(f"df after: {df}")
    return df.to_dict("records")

    # Compare models with PSIS-LOO
    # mods = {"LN": idata_l, "Gamma": idata_g, "Weibull": idata_w, "NB": idata_n}
    # loo = az.compare(mods, ic="loo")

    # az.plot_compare(loo, insample_dev=True, plot_kwargs={"color_insample_dev":"crimson", "color_dse":"steelblue"})
    # plt.xlabel("ELPD LOO")
    # plt.title("LOO Model Comparison (Italy)", size=12)
    # plt.grid(alpha=0.3)
    # plt.legend(prop={"size": 12})
    # plt.tight_layout()
    # plt.savefig("./model_comparison/IT_model_comp_loo.png", dpi=600)
    # plt.show()
    # plt.close()
    # loo_df = pd.DataFrame(loo)
    # loo_df.to_csv("./model_comparison/IT_model_comp_loo.csv")

    # Compare models with WAIC
    # mods = {"LN": idata_l, "Gamma": idata_g, "Weibull": idata_w, "NB": idata_n}
    # waic = az.compare(mods, ic="waic")

    # az.plot_compare(loo, insample_dev=True, plot_kwargs={"color_insample_dev":"crimson", "color_dse":"steelblue"})
    # plt.xlabel("Log")
    # plt.title("Waic Model Comparison (Italy)", size=12)
    # plt.grid(alpha=0.3)
    # plt.legend(prop={"size": 12})
    # plt.tight_layout()
    # plt.savefig("./model_comparison/IT_model_comp_waic.png", dpi=600)
    # plt.show()
    # plt.close()
    # loo_df = pd.DataFrame(loo)
    # loo_df.to_csv("./model_comparison/IT_model_comp_waic.csv")
