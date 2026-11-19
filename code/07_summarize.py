"""Step 7: average CARs by era and anchor, with plain t-tests, and the main figure.

Outputs:
  outputs/car_summary.csv          one row = sample x anchor x era x CAR window. mean is a decimal
                                   (0.01 = 1%). With n this small (v0), the t-stats mean little.
                                   n = additions, n_dates = distinct day 0s. The *_by_date columns
                                   are the same t-test on one average CAR per day 0 (audit A3).
  outputs/fig_mean_car_by_era.png  mean cumulative AR, day -10 to +10
                                   left: effective anchor, one line per era
                                   right: 2022+ releases, announce vs. effective
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

from config import CLEAN, ERAS, OUTPUTS

SUMMARY_OUT = OUTPUTS / "car_summary.csv"
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
car_windows = pd.read_csv(OUTPUTS / "car_windows.csv")
car_long = car_windows.melt(id_vars=["sample", "anchor", "era", "day0"], value_vars=list(CAR_COLUMNS),
                            var_name="window", value_name="car")

# One test over events, as agreed at Checkpoint 1.
by_event = car_long.groupby(GROUP)["car"].apply(t_test).unstack()
# Additions in the same release share day 0, so their CARs share the same market and sector news
# and are not independent (audit A3). n_dates = distinct day 0s. The second test averages the CARs
# that share a day 0 first, then runs the same plain t-test over dates.
by_event["n_dates"] = car_long.groupby(GROUP)["day0"].nunique()
by_date = (car_long
           .groupby([*GROUP, "day0"])["car"].mean()
           .groupby(GROUP).apply(t_test).unstack()
           .drop(columns="n")
           .add_suffix("_by_date"))
car_summary = (by_event.join(by_date, validate="one_to_one")
               .reset_index()
               .assign(window=lambda d: d["window"].map(CAR_COLUMNS))
               .astype({"n": int, "n_dates": int})
               [[*GROUP, "n", "n_dates", "mean", "t_stat", "p_value",
                 "mean_by_date", "t_stat_by_date", "p_value_by_date"]])
assert (car_summary["n_dates"] <= car_summary["n"]).all()
car_summary.to_csv(SUMMARY_OUT, index=False)
print(car_summary.round(4).to_string())

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
fig.text(0.01, 0.01, "v0 sample only (small n). Market model vs. SPY, estimation days -250 to -30.",
         fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.04, 0.97, 1))
fig.savefig(FIGURE_OUT, dpi=150, facecolor="white")
print(f"saved {FIGURE_OUT.name}")
