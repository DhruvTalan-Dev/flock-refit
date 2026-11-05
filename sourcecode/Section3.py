import pandas as pd
import numpy as np
from pathlib import Path
from Section2 import load, HOUSES      # reuse Part 2: 1-minute Aggregate + WM for each house
import time
from sklearn.ensemble import HistGradientBoostingRegressor
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = Path(__file__).parent.parent
PLOTS = ROOT / "plots"
SHOW = False
V1 = ["agg", "diff", "mean_30", "max_30", "min_30", "std_30", "above_base", "hour"]   # model v1: first 7 inputs
V2 = V1 + ["heat_now", "since_heat"]                                                   # model v2: + heating idea

def load_all():
    data = {}
    for h in HOUSES:
        df1 = load(h)
        both = df1["Aggregate"].notna() & df1["WM"].notna()      # minutes we can use
        #for each house , it counts the minutes where both the Aggregate and the washing machine have data.
        print(f"  minutes with Aggregate + WM: {both.sum()} ({both.mean() * 100:.1f}%)")
        data[h] = df1
    return data

def add_heat(X, low=1500, high=3000, heat_len=5):
    hot = X["above_base"].between(low, high)                      # 1,500-3,000 W above the base load
    run_id = (hot != hot.shift()).cumsum().to_numpy()             # number each run of hot / not-hot minutes
    run_len = hot.groupby(run_id).transform("size")               # length of the run each minute is in
    heat = (hot & (run_len >= heat_len)).to_numpy()               # heating = hot for 5+ minutes in a row
    X["heat_now"] = heat.astype(int)                              # 8. heating right now (1 = yes)
    pos = np.arange(len(X))
    last = pd.Series(np.where(heat, pos, np.nan)).ffill().to_numpy()   # row of the last heating minute
    X["since_heat"] = pos - last                                  # 9. minutes since heating (0 = now)
    return X

def make_inputs(df1):
    agg = df1["Aggregate"]
    # windows count rows, not clock time: each row = 1 real minute (safe with the repeated October hour)
    win = agg.rolling(31, center=True, min_periods=1)            # 15 min before + this minute + 15 after
    X = pd.DataFrame(index=df1.index)
    X["agg"] = agg                                                # 1. Aggregate now
    X["diff"] = agg.diff()                                        # 2. change from 1 minute before
    X["mean_30"] = win.mean()                                     # 3. average in the 30 min around
    X["max_30"] = win.max()                                       # 4. highest ...
    X["min_30"] = win.min()                                       #    ... and lowest in the 30 min around
    X["std_30"] = win.std()                                       # 5. how bumpy the power is
    base = agg.rolling(121, center=True, min_periods=1).min()     # lowest value in the 2 h around
    X["above_base"] = agg - base                                  # 6. power above the always-on load
    X["hour"] = df1.index.hour
    X = add_heat(X)  # 7. hour of day (0-23)
    y = df1["WM"]                                                 # what the model must guess
    return X, y

def score(y, guess, agg, on_w=20):
    ok = y.notna() & agg.notna()                          # only minutes with Aggregate + WM
    y, guess = y[ok], guess[ok]
    mae = (y - guess).abs().mean()                        # 1. average error per minute (W)
    energy = (guess.sum() - y.sum()) / y.sum() * 100      # 2. total energy error (%)
    on, said_on = y > on_w, guess > on_w                  # 3. ON = more than 20 W (same as Part 2)
    hit = (on & said_on).sum()                            #    minutes ON in both
    precision = hit / said_on.sum() if said_on.sum() else 0.0
    recall = hit / on.sum()
    f1 = 2 * precision * recall / (precision + recall) if hit else 0.0
    return {"mae": mae, "energy": energy, "f1": f1, "precision": precision, "recall": recall}


def show(h, name, s):
    print(f"  House {h:>2} | {name:<10} | MAE {s['mae']:6.1f} W | energy {s['energy']:5.0f}%"
          f" | F1 {s['f1']:.2f} (precision {s['precision']:.2f}, recall {s['recall']:.2f})")

def profile_guess(inp, test_h):
    train = [inp[h] for h in HOUSES if h != test_h]               # the other 3 houses only
    hours = pd.concat([X["hour"][y.notna()] for X, y in train])
    wm = pd.concat([y[y.notna()] for X, y in train])
    avg = wm.groupby(hours.to_numpy()).mean()                     # 24 values: average WM per hour
    print(f"  profile (without House {test_h}): highest at {avg.idxmax()}:00 = {avg.max():.0f} W")
    return inp[test_h][0]["hour"].map(avg)                        # test house: look up its hour

def train_predict(inp, test_h, cols):
    train = [inp[h] for h in HOUSES if h != test_h]               # the other 3 houses only
    X_tr = pd.concat([X.loc[y.notna().to_numpy(), cols] for X, y in train])   # minutes with a WM reading
    y_tr = pd.concat([y[y.notna()] for X, y in train])
    t0 = time.time()
    model = HistGradientBoostingRegressor(early_stopping=False, random_state=0)   # fresh model each round
    model.fit(X_tr, y_tr)
    print(f"  model (without House {test_h}): trained on {len(y_tr)} minutes in {time.time() - t0:.0f} s")
    X_te = inp[test_h][0][cols]
    guess = model.predict(X_te).clip(0, None)                     # power can't be below 0 W
    return pd.Series(guess, index=X_te.index)


def plot_pred(X, y, guess, house, day):
    PLOTS.mkdir(exist_ok=True)
    d = X.index.normalize() == pd.Timestamp(day)                  # boolean mask (repeated October hour)
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(X.index[d], X["agg"][d], lw=0.8, color="grey", label="Aggregate (whole house)")
    ax.plot(X.index[d], y[d], lw=1.2, color="tab:blue", label="Washing machine: actual")
    ax.plot(X.index[d], guess[d], lw=1.2, color="tab:orange", label="Washing machine: predicted")
    ax.set_title(f"House {house} (test house, not used in training): {day}")
    ax.set_ylabel("Power (W)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(PLOTS / f"part3_actual_vs_pred_house{house}.png", dpi=120)
    print(f"part3_actual_vs_pred_house{house}.png created and saved in plots folder")
    if SHOW:
        plt.show()
    plt.close(fig)



def run():
    data = load_all()
    inp = {h: make_inputs(data[h]) for h in HOUSES}               # the 7 inputs + WM, each house

    print("=" * 20)
    print("CHECKING BASELINE 1, ALWAYS OFF ...")
    for h in HOUSES:
        X, y = inp[h]
        off = pd.Series(0.0, index=y.index)                       # always 0 W
        show(h, "always-off", score(y, off, X["agg"]))

    print("=" * 20)
    print("CHECKING BASELINE 2, USAGE PROFILE ...")
    for h in HOUSES:                                              # 4 rounds: house h = test house
        X, y = inp[h]
        prof = profile_guess(inp, h)                              # built from the other 3 houses
        show(h, "profile", score(y, prof, X["agg"]))

    guesses = {}
    for name, cols in [("model v1", V1), ("model v2", V2)]:
        print("=" * 20)
        print(f"CHECKING {name.upper()} (GRADIENT BOOSTING) ...")
        for h in HOUSES:  # 4 rounds: house h = test house
            X, y = inp[h]
            guess = train_predict(inp, h, cols)  # trained on the other 3 houses
            show(h, name, score(y, guess, X["agg"]))
            guesses[(name, h)] = guess  # keep for the plot

    print("=" * 20)
    print("PLOT: ACTUAL VS PREDICTED (MODEL V2) ...")
    X, y = inp[2]
    plot_pred(X, y, guesses[("model v2", 2)], 2, "2013-09-20")  # same day as Part 2 Plot 1

if __name__ == "__main__":
    run()