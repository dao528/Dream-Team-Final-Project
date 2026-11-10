"""Step 7: average CARs by era and anchor, with plain t-tests, and the main figure.

Outputs:
  outputs/car_summary.csv          one row = sample x anchor x era x CAR window
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
CAR_COLUMNS = {"car_0_p1": "CAR[0,+1]", "car_m1_p1": "CAR[-1,+1]"}
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


car_windows = pd.read_csv(OUTPUTS / "car_windows.csv")
car_summary = (car_windows
               .melt(id_vars=["sample", "anchor", "era"], value_vars=list(CAR_COLUMNS),
                     var_name="window", value_name="car")
               .groupby(["sample", "anchor", "era", "window"])["car"]
               .apply(t_test)
               .unstack()
               .reset_index()
               .assign(window=lambda d: d["window"].map(CAR_COLUMNS)))
car_summary["n"] = car_summary["n"].astype(int)
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
