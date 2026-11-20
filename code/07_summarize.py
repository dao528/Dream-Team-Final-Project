"""Step 7: average CARs by era and anchor, with plain t-tests, and the main figure.

Outputs:
  outputs/car_summary.csv          one row = sample x anchor x era x CAR window. mean is a decimal
                                   (0.01 = 1%). With n this small (v0), the t-stats mean little.
                                   Additions announced in the same release share their day 0s and
                                   market news, so they are not independent (audit finding A3).
                                   n_dates counts distinct day 0s, and the *_by_date columns repeat
                                   the t-test on one average CAR per day 0.
  outputs/car_summary_history_dates.csv  the same for the 2001-2021 additions only, in four subsamples
                                   (audit A1): all additions; only the ones that pass the v0 volume
                                   filter; without the ambiguous dates; only the ones where Key Dev
                                   and Wikipedia give the same effective date (date_rule in 03b).
  outputs/fig_mean_car_by_era.png  mean cumulative AR, day -10 to +10
                                   left: effective anchor, one line per era
                                   right: 2022+ releases, announce vs. effective
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

from config import CLEAN, ERAS, HISTORY_PER_ERA, OUTPUTS, POC_TICKERS

SUMMARY_OUT = OUTPUTS / "car_summary.csv"
HISTORY_SUMMARY_OUT = OUTPUTS / "car_summary_history_dates.csv"
FIGURE_OUT = OUTPUTS / "fig_mean_car_by_era.png"
CAR_COLUMNS = {"car_0_p1": "CAR[0,+1]", "car_m1_p1": "CAR[-1,+1]", "car_m10_p10": "CAR[-10,+10]"}
# Default categorical palette, slots 1-4, checked with the dataviz validator (light surface).
ERA_COLORS = dict(zip(ERAS, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]))
ANCHOR_COLORS = {"announce": "#2a78d6", "effective": "#eb6834"}
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3de"


def t_test(cars):
    """Mean CAR, its t-stat and p-value against zero (plain one-sample t-test)."""
    if len(cars) < 2:
        return pd.Series({"n": len(cars), "mean": cars.mean(), "t_stat": float("nan"), "p_value": float("nan")})
    result = stats.ttest_1samp(cars, 0.0)
    return pd.Series({"n": len(cars), "mean": cars.mean(), "t_stat": result.statistic, "p_value": result.pvalue})


GROUP = ["sample", "anchor", "era", "window"]
# History robustness (audit A1): which 2001-2021 additions enter each row of car_summary_history_dates.csv.
HISTORY_SUBSAMPLES = {
    "all": lambda d: d["event_id"].notna(),
    "v0 volume filter": lambda d: d["passes_volume_filter"].eq(True),
    "without ambiguous dates": lambda d: d["date_rule"] != "ambiguous",
    "Key Dev and Wikipedia agree": lambda d: d["date_rule"] == "agree",
}


def summarize(cars):
    """t-test per GROUP over events, and again over one average CAR per day 0 (additions that share
    a day 0 are averaged first, audit A3)."""
    by_event = cars.groupby(GROUP)["car"].apply(t_test).unstack()
    by_date = (cars.groupby(GROUP + ["day0"])["car"].mean()
               .groupby(GROUP).apply(t_test).unstack()
               .rename(columns={"n": "n_dates", "mean": "mean_by_date", "t_stat": "t_stat_by_date",
                                "p_value": "p_value_by_date"}))
    summary = (by_event.join(by_date, validate="one_to_one")
               .reset_index()
               .assign(window=lambda d: d["window"].map(CAR_COLUMNS))
               .astype({"n": int, "n_dates": int}))
    assert (summary["n_dates"] <= summary["n"]).all()
    return summary


car_windows = pd.read_csv(OUTPUTS / "car_windows.csv")
cars = car_windows.melt(id_vars=["event_id", "sample", "anchor", "era", "day0"], value_vars=list(CAR_COLUMNS),
                        var_name="window", value_name="car")
car_summary = summarize(cars)
car_summary.to_csv(SUMMARY_OUT, index=False)
print(car_summary.round(4).to_string())

events = pd.read_csv(CLEAN / "events.csv", usecols=["event_id", "date_rule", "passes_volume_filter"])
history_cars = (cars
                .query("sample == 'keydev_history'")
                .merge(events, on="event_id", how="left", validate="many_to_one", indicator=True))
assert (history_cars["_merge"] == "both").all()
history_summary = pd.concat([summarize(history_cars[keep(history_cars)]).assign(subsample=name)
                             for name, keep in HISTORY_SUBSAMPLES.items()], ignore_index=True)
history_summary = history_summary[["subsample"] + [c for c in history_summary.columns if c != "subsample"]]
history_summary.to_csv(HISTORY_SUMMARY_OUT, index=False)
print(history_summary.query("window == 'CAR[0,+1]'")[["subsample", "era", "n", "mean", "t_stat"]]
      .round(4).to_string(index=False))

# Mean cumulative AR by event day.
event_panel = pd.read_csv(CLEAN / "event_panel.csv")
mean_path = event_panel.groupby(["sample", "anchor", "era", "event_day"], as_index=False).agg(
    mean_car=("car_to_date", "mean"), n=("event_id", "nunique"))

fig, (ax_era, ax_anchor) = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax in (ax_era, ax_anchor):
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.axvline(0, color=GRID, linewidth=1, zorder=0)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.set_xlabel("Trading days relative to day 0", color=INK)
    ax.set_xticks(range(-10, 11, 5))


def plot_lines(ax, paths, key, colors):
    """One line per group, labelled at its right end (labels instead of only a legend)."""
    for label, path in paths.groupby(key):
        ax.plot(path["event_day"], path["mean_car"] * 100, color=colors[label], linewidth=2,
                label=f"{label} (n={path['n'].max()})")
        last = path.iloc[-1]
        ax.annotate(label, (last["event_day"], last["mean_car"] * 100), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8, color=INK)
    ax.legend(frameon=False, fontsize=8, loc="upper left", labelcolor=INK)


plot_lines(ax_era, mean_path.query("anchor == 'effective'"), "era", ERA_COLORS)
ax_era.set_title("Effective date (day 0 = rebalance close), by era", color=INK, fontsize=10, loc="left")
ax_era.set_ylabel("Mean cumulative abnormal return (%)", color=INK)
plot_lines(ax_anchor, mean_path.query("sample == 'releases_2022on'"), "anchor", ANCHOR_COLORS)
ax_anchor.set_title("2022+ additions: announcement vs. effective date", color=INK, fontsize=10, loc="left")
history_note = "all Key Dev additions" if HISTORY_PER_ERA is None else f"{HISTORY_PER_ERA} Key Dev additions per era"
release_note = "all additions" if POC_TICKERS is None else f"{len(POC_TICKERS)} additions (v0)"
fig.text(0.01, 0.01, f"2001-2021: {history_note}. 2022+: {release_note}. Market model vs. SPY, "
         "estimation days -250 to -30.", fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.04, 0.97, 1))
fig.savefig(FIGURE_OUT, dpi=150, facecolor="white")
print(f"saved {FIGURE_OUT.name}")
