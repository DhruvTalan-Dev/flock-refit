import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt


ROOT = Path(__file__).parent.parent     # goes to base folder
DATA = ROOT / "data"                    # the / joins folder names
P1 = DATA / "RAW_House1_Part1.csv"
P2 = DATA / "RAW_House1_Part2.csv"
COLS = ["Aggregate"] + [f"Appliance{i}" for i in range(1, 10)]
PLOTS = ROOT / "plots"
SHOW = {"Aggregate": "Aggregate", "Appliance1": "Fridge", "Appliance5": "Washing machine"}
SHOW1 = False

LIMITS = {
    "Aggregate": 12000, #ALTHOUGH THE PEAKJ IS NEAR TO 10.5 kW , 1.5kW are added so that the plot not shows as cut off
    "Appliance1": 200,    # Fridge
    "Appliance2": 150,    # Freezer (1)
    "Appliance3": 200,    # Freezer (2)
    "Appliance4": 2400,   # Washer dryer
    "Appliance5": 2600,   # Washing machine #400 W are added so that the plot not shows as cut off
    "Appliance6": 2400,   # Dishwasher
    "Appliance7": 280,    # Computer
    "Appliance8": 135,    # TV
    "Appliance9": 2000,   # Heater
}


def info(name, df):
    t = pd.to_datetime(df.iloc[:, 1], unit="s")   # column 2 = UNIX
    print(name)
    print("  rows   :", len(df))
    print("  start  :", t.min())
    print("  end    :", t.max())
    print("  columns:", list(df.columns))
    print()

def overlap(p1, p2):
    start = p2["Unix"].min()          # Part2 starts
    end = p1["Unix"].max()            # Part1 ends
    a = p1[(p1["Unix"] >= start) & (p1["Unix"] <= end)]
    b = p2[(p2["Unix"] >= start) & (p2["Unix"] <= end)]

    print("Overlap window rows in Part1:", len(a))
    print("Overlap window rows in Part2:", len(b))
    print("Same Unix in both    :", a["Unix"].isin(b["Unix"]).sum())



def combine(p1, p2):
    # Part1: fake 0s -> NaN
    p1 = p1.copy()
    p1[COLS] = p1[COLS].astype(float)
    p1.loc[(p1[COLS] == 0).all(axis=1), COLS] = float("nan")   # whole row 0
    p1.loc[p1["Aggregate"] == 0, "Aggregate"] = float("nan")    # Aggregate 0

    # Part1 until Part2 starts, then Part2
    cut = p2["Unix"].min()
    df = pd.concat([p1[p1["Unix"] < cut], p2], ignore_index=True)
    print("Combined rows:", len(df))
    return df


def dfinfo(df):
    df = df.sort_values("Unix")  # oldest first
    print(df["Time"].head(20))

    t = pd.to_datetime(df["Unix"], unit="s")
    per_min = t.dt.floor("1min").value_counts().sort_index()  # rows in each minute

    # print(per_min.head(5))                             # first 5 minutes, check 14:07 = 8
    print("Average rows per minute:", per_min.mean())



def check_time(df):
    t = pd.to_datetime(df["Unix"], unit="s", errors="coerce")
    print("Bad timestamps :", t.isna().sum())
    print("Out of order   :", (df["Unix"].diff() < 0).sum())

def check_dupes(df):
    print("Repeated times     :", df["Unix"].duplicated().sum())
    print("Repeated full rows :", df.duplicated(subset=["Unix"] + COLS).sum())


def fix_dupes(df):
    n0 = len(df)
    df = df.sort_values("Unix", kind="stable")

    # Rule 2: exact copies -> keep one
    df = df.drop_duplicates(subset=["Unix"] + COLS).reset_index(drop=True)
    n1 = len(df)

    # Rule 3: same second, different values -> keep the one that changed most
    pos = df.groupby("Unix").cumcount().to_numpy()          # 0 = 1st row in that second, 1 = 2nd ...
    prev = df[COLS].reindex(df.index.to_numpy() - pos - 1)  # the row just before that second
    prev.index = df.index
    df["change"] = (df[COLS] - prev).abs().sum(axis=1)      # NaN is skipped (counts as 0)

    best = df.groupby("Unix")["change"].idxmax()            # biggest change; tie -> first row
    df = df.loc[best].drop(columns="change")

    print("Rows before          :", n0)
    print("Exact copies removed :", n0 - n1)
    print("Same-second removed  :", n1 - len(df))
    print("Rows left            :", len(df))
    print("Repeated times left  :", df["Unix"].duplicated().sum())
    return df



def check_missing(df):
    n = df[COLS].isna().sum()                     # NaN count per column
    print(pd.DataFrame({"missing": n, "%": (n / len(df) * 100).round(2)}))
    print("Whole row missing:", df[COLS].isna().all(axis=1).sum())

def check_gaps(df):
    gap = df["Unix"].diff()                       # seconds since the row before
    print("Normal gap (median, s):", gap.median())

    bins = [0, 8, 60, 120, 600, 3600, float("inf")]
    names = ["<= 8 s", "8 s - 1 min", "1 - 2 min", "2 - 10 min", "10 min - 1 h", "> 1 h"]
    print(pd.cut(gap, bins=bins, labels=names).value_counts(sort=False))

    print("\n5 biggest gaps:")
    for i, g in gap.nlargest(5).items():
        end = df.loc[i, "Unix"]
        print(" ", pd.to_datetime(end - g, unit="s"), "->", pd.to_datetime(end, unit="s"), f"({g / 3600:.1f} h)")


def check_extreme(df):
    apps = COLS[1:]                                  # the 9 appliances
    print(df[COLS].agg(["min", "max"]).T)            # smallest and biggest per column
    print("\nNegative values:", (df[COLS] < 0).sum().sum())
    print("\nAppliance > 4000 W:")
    print((df[apps] > 4000).sum())



def mark_bad(df):
    df = df.copy()
    for col, limit in LIMITS.items():
        bad = (df[col] < 0) | (df[col] > limit)           # impossible or too high
        print(f"{col:11}: {bad.sum():>8} bad ({bad.mean() * 100:.2f}%)")
        df.loc[bad, col] = float("nan")                   # bad -> NaN
    return df

def resample_1min(df):
    t = pd.to_datetime(df["Unix"], unit="s")
    df1 = df.set_index(t)[COLS].resample("1min").mean()    # average per minute
    print("1-min rows    :", len(df1))
    print("Empty minutes :", df1.isna().all(axis=1).sum())  # no data at all
    return df1



def fill_short(df1, max_gap=2):
    df1 = df1.copy()
    for col in COLS:
        miss = df1[col].isna()
        run_id = (~miss).cumsum()                          # each NaN run gets one id
        run_len = miss.groupby(run_id).transform("sum")    # length of that NaN run
        short = miss & (run_len <= max_gap) & (run_id > 0) # runs of 1-2 minutes, with a value before
        df1.loc[short, col] = df1[col].ffill()[short]      # copy the last value
        print(f"{col:11}: filled {short.sum():>7}, still NaN {df1[col].isna().sum():>7}")
    return df1


def flag_outages(df1):
    df1 = df1.copy()
    df1["outage"] = df1["Aggregate"].isna().astype(int)              # 1 = long gap
    starts = (df1["outage"] == 1) & (df1["outage"].shift() != 1)    # first minute of each outage
    print("Outage minutes :", df1["outage"].sum())
    print("Outages (count):", starts.sum())
    print("Outage hours   :", round(df1["outage"].sum() / 60, 1))
    return df1

def plot_before_after(raw, df1):
    PLOTS.mkdir(exist_ok=True)
    raw = raw.sort_values("Unix")
    t_raw = pd.to_datetime(raw["Unix"], unit="s")

    fig, ax = plt.subplots(3, 2, figsize=(14, 9), sharex=True)
    for i, (col, name) in enumerate(SHOW.items()):
        ax[i, 0].plot(t_raw, raw[col], lw=0.3, color="grey")      # before: raw readings
        ax[i, 0].set_title(f"{name}: before (raw)")
        ax[i, 0].set_ylabel("Power (W)")
        ax[i, 1].plot(df1.index, df1[col], lw=0.3)                 # after: clean 1-min
        ax[i, 1].set_title(f"{name}: after (clean, 1 min)")
    fig.autofmt_xdate()                                            # tilt dates so they don't overlap
    fig.tight_layout()
    fig.savefig(PLOTS / "part1_before_after.png", dpi=120)
    print(f"part1_before_after.png created and saved in plots folder")
    if SHOW1:
        plt.show()
    plt.close(fig)

def save_clean(df1):
    out = DATA / "House1_clean_1min.csv"
    df1.to_csv(out, index_label="Time_UTC")       # time column + 10 power columns + outage
    print("Saved:", out, "|", len(df1), "rows")



def run():
    print("=" * 20)
    print("LOADING RAW FILES ...")
    p1 = pd.read_csv(P1)
    p2 = pd.read_csv(P2)
    info("Part1", p1)
    info("Part2", p2)

    print("=" * 20)
    print("CHECKING OVERLAP OF PART1 AND PART2 ...")
    overlap(p1, p2)

    print("=" * 20)
    print("COMBINING PART1 + PART2 ...")
    raw = combine(p1, p2)

    print("=" * 20)
    print("CHECKING TIMESTAMPS ...")
    check_time(raw)                  # NEW: bad timestamps + rows out of order (DATA.md 3.1)

    print("=" * 20)
    print("CHECKING DUPLICATES ...")
    check_dupes(raw)                 # NEW: repeated seconds (DATA.md 3.2)

    print("=" * 20)
    print("REMOVING DUPLICATES ...")
    df = fix_dupes(raw)

    print("=" * 20)
    print("CHECKING MISSING, GAPS, EXTREME VALUES ...")
    check_missing(df)
    check_gaps(df)
    check_extreme(df)

    print("=" * 20)
    print("CLEANING ...")
    df = mark_bad(df)
    df1 = resample_1min(df)
    df1 = fill_short(df1)
    df1 = flag_outages(df1)

    print("=" * 20)
    print("PLOT + SAVE ...")
    plot_before_after(raw, df1)
    print("check plot in plots folder")
    save_clean(df1)



if __name__ == "__main__":
    run()




