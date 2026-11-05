import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
PLOTS = ROOT / "plots"
SHOW = False
PEOPLE = {2: 4, 15: 1, 16: 6, 17: 3}      # from the readme

# house: washing machine column (from the cleaned readme)
HOUSES = {2: "Appliance2", 15: "Appliance3", 16: "Appliance5", 17: "Appliance4"}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def load(house):
    small = DATA / f"House{house}_wm_1min.pkl"
    if small.exists():
        df1 = pd.read_pickle(small)                      # fast: already made
    else:
        col = HOUSES[house]
        df = pd.read_csv(DATA / f"CLEAN_House{house}.csv", usecols=["Unix", "Aggregate", col])
        t = pd.to_datetime(df["Unix"], unit="s", utc=True).dt.tz_convert("Europe/London")
        df1 = df.set_index(t)[["Aggregate", col]].resample("1min").mean()
        df1 = df1.rename(columns={col: "WM"})
        df1.index = df1.index.tz_localize(None)          # keep UK clock time, drop the +00/+01 label
        df1.to_pickle(small)                             # save for next time
    print(f"House {house}: {len(df1)} minutes | {df1.index.min()} -> {df1.index.max()}")
    return df1


def quality(df1):
    n = len(df1)
    miss = df1["WM"].isna().sum()
    zero = (df1["WM"] == 0).sum()
    above = (df1["WM"] > 0).sum()
    weeks = (n - miss) / 10080                       # minutes with data / minutes in a week
    print(f"  missing: {miss} ({miss / n * 100:.1f}%) | zero: {zero} ({zero / n * 100:.1f}%)"
          f" | above 0 W: {above / n * 100:.1f}%")
    print(f"  WM max: {df1['WM'].max():.0f} W | weeks with data: {weeks:.1f}")
    return weeks

def find_cycles(df1, on_w=20, gap=3, heat_w=1500, heat_len=5, end_gap=30, min_len=30):
    wm = df1["WM"]
    times = df1.index

    # Rule 1: ON = more than 20 W (missing minutes count as OFF)
    on = (wm > on_w).to_numpy()

    # Rule 4 (part 1): heating = 1500 W or more for 5 minutes in a row
    hot = (wm >= heat_w).astype(int)
    heat = hot.rolling(heat_len).sum().eq(heat_len).to_numpy()

    # Step A: cut the ON minutes into small pieces (tiny 1-2 min breaks are joined)
    pieces = []
    start = last = None
    for i in range(len(on)):
        if not on[i]:
            continue
        if start is None:
            start = i
        elif i - last - 1 >= gap:
            pieces.append((start, last))
            start = i
        last = i
    if start is not None:
        pieces.append((start, last))

    # Step B: join pieces into washes
    washes = []                                          # each wash: [start, end, had_heating]
    for s, e in pieces:
        has_heat = bool(heat[s:e + 1].any())
        if washes:
            short_break = s - washes[-1][1] - 1 < end_gap     # Rules 2 + 3: break under 30 min?
            second_heat = has_heat and washes[-1][2]          # Rule 4 (part 2): a 2nd heating?
            if short_break and not second_heat:
                washes[-1][1] = e                             # same wash -> make it longer
                washes[-1][2] = washes[-1][2] or has_heat
                continue
        washes.append([s, e, has_heat])                       # otherwise -> new wash

    cyc = pd.DataFrame([(times[s], times[e], e - s + 1, h) for s, e, h in washes],
                       columns=["start", "end", "minutes", "heated"])

    # Rule 5: a wash must last at least 30 minutes
    cyc = cyc[cyc["minutes"] >= min_len].reset_index(drop=True)
    print(f"  cycles: {len(cyc)} | median length: {cyc['minutes'].median()} min"
          f" | with heating: {cyc['heated'].sum()} | without: {(~cyc['heated']).sum()}")
    return cyc


def usage(cyc):
    start = cyc["start"]                                   # 1. each wash counted once, at its start

    # 2. % of washes starting in each hour (0-23)
    hour = start.dt.hour.value_counts(normalize=True).reindex(range(24), fill_value=0) * 100

    # 3. % of washes on each day (0 = Mon ... 6 = Sun)
    day = start.dt.day_of_week.value_counts(normalize=True).reindex(range(7), fill_value=0) * 100

    # 4. weekend share (even spread would be 28.6%)
    weekend = day[5] + day[6]
    print(f"  busiest hour: {hour.idxmax()}:00 ({hour.max():.1f}%)"
          f" | busiest day: {DAYS[day.idxmax()]} ({day.max():.1f}%)"
          f" | weekend: {weekend:.1f}%")
    return hour, day



def pick_day(df1, cyc, at_least=1, at_most=1):
    dates = df1.index.normalize()
    n = cyc["start"].dt.normalize().value_counts()             # washes per day
    for day in sorted(n[(n >= at_least) & (n <= at_most)].index):
        d = df1[dates == day]
        if len(d) == 1440 and d.notna().all().all():           # full day, nothing missing
            return day

def plot_day(df1, cyc, house):
    PLOTS.mkdir(exist_ok=True)
    day = pick_day(df1, cyc)
    d = df1[df1.index.normalize() == day]
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(d.index, d["Aggregate"], lw=0.8, color="grey", label="Aggregate (whole house)")
    ax.plot(d.index, d["WM"], lw=1.2, color="tab:blue", label="Washing machine")
    ax.set_title(f"House {house}: one day ({day.date()})")
    ax.set_ylabel("Power (W)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS / f"part2_day_house{house}.png", dpi=120)
    print("  Plot 1 day:", day.date())
    print(f"part2_day_house{house}.png created and saved in plots folder")
    if SHOW:
        plt.show()
    plt.close(fig)

def plot_cycles(df1, cyc, house):
    PLOTS.mkdir(exist_ok=True)
    day = pick_day(df1, cyc, at_least=2, at_most=99)            # a day with 2 or more washes
    d = df1[df1.index.normalize() == day]
    today = cyc[cyc["start"].dt.normalize() == day]
    top = d["WM"].max()
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(d.index, d["WM"], lw=1, color="tab:blue", label="Washing machine")
    for i, c in enumerate(today.itertuples(), start=1):
        ax.axvspan(c.start, c.end + pd.Timedelta("1min"), color="orange", alpha=0.25,
                   label="Detected wash" if i == 1 else None)
        ax.text(c.start, top * 1.03, f"Wash {i}: {c.minutes} min", fontsize=9)
    ax.set_xlim(day, day + pd.Timedelta("1D"))
    ax.set_ylim(0, top * 1.15)
    ax.set_title(f"House {house}: detected washes on {day.date()}")
    ax.set_ylabel("Power (W)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(PLOTS / f"part2_cycles_house{house}.png", dpi=120)
    print("  Plot 2 day:", day.date(), "| washes:", len(today))
    print(f"part2_cycles_house{house}.png created and saved in plots folder")
    if SHOW:
        plt.show()
    plt.close(fig)

def plot_lengths(all_cyc):
    PLOTS.mkdir(exist_ok=True)
    houses = list(all_cyc)
    data = [all_cyc[h]["minutes"] for h in houses]       # wash lengths of each house

    # numbers for RESULTS.md
    for h, m in zip(houses, data):
        print(f"House {h}: washes {len(m)} | median {m.median():.0f} min"
              f" | middle half {m.quantile(0.25):.0f}-{m.quantile(0.75):.0f} min")

    # Plot 3: one box per house
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.boxplot(data)
    ax.set_xticks(range(1, len(houses) + 1),
                  [f"House {h}\npeople: {PEOPLE[h]}" for h in houses])
    ax.set_ylabel("Wash length (min)")
    ax.set_title("Wash length per house")
    fig.tight_layout()
    fig.savefig(PLOTS / "part2_length_houses.png", dpi=120)
    print(f"part2_length_houses.png created and saved in plots folder")
    if SHOW:
        plt.show()
    plt.close(fig)



def run():
    all_cyc = {}
    for h in HOUSES:
        print(f"House: {h}")

        print("="*20)

        print("LOADING DATA .. ")
        df1 = load(h)

        print("=" * 20)

        print("QUALITY OF DATA .. ")
        weeks = quality(df1)

        print("=" * 20)

        print(f"CYCLES FOR A HOUSE {h} .. ")
        cyc = find_cycles(df1)
        print(f"  washes per week: {len(cyc) / weeks:.1f}")

        print("=" * 20)

        print("USAGE BY HOUR AND DAY .. ")
        hour, day = usage(cyc)

        print("=" * 20)

        all_cyc[h] = cyc
        if h == 2:

            plot_day(df1, cyc, h)
            print("check plot in plots folder")

            print("=" * 20)


        if h == 15:
            plot_cycles(df1, cyc, h)
            print("check plot in plots folder")

            print("=" * 20)

    plot_lengths(all_cyc)
    print("check plot in plots folder")

    print("=" * 20)

if __name__ == "__main__":
    run()