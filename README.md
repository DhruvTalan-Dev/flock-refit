# Flock Energy take-home: REFIT data cleaning and washing-machine disaggregation

## In one minute

- **Goal:** clean raw home electricity data, study how washing machines are used, and build a model that guesses the washing machine's power using only the whole-house meter.
- **Data:** REFIT Electrical Load Measurements: 20 UK homes, University of Strathclyde.
- **Main result:** in homes it has never seen, the model finds **when** a wash happens much better than simple baselines (F1 0.32–0.75 vs 0.14 or less). But its **kWh numbers are not reliable yet** (energy error −62% to +98%). The main reason is that other ~2 kW heating appliances look like the washing machine in the whole-house power.

## Where to read what

| File | What is inside |
|---|---|
| [DATA.md](DATA.md) | Part 1: checks on raw House 1 data, cleaning steps, remaining concerns |
| [RESULTS.md](RESULTS.md) | Part 2: washing-machine analysis and plots. Part 3: model, testing, results, failure cases |
| [Recommendation.md](Recommendation.md) | One-page summary for a utility, plus the Part 4 answers |
| README.md | This file: how to run the code, main choices, AI tools used, next steps |

## What I built

1. **Part 1, cleaning** (`sourcecode/Section1.py`): takes House 1 raw data and joins its two files, sorts the rows, removes duplicates, marks impossible values as missing, averages to 1 minute, fills 1–2 minute gaps, flags longer outages, and makes a before/after plot.
2. **Part 2, washing-machine analysis** (`sourcecode/Section2.py`): 4 homes (Houses 2, 15, 16, 17) from the cleaned data at 1 minute. A simple rule finds each wash. Reports data quality, washes per week, busiest hour and day, wash length per home, and 3 plots.
3. **Part 3, model** (`sourcecode/Section3.py`): a gradient boosting model guesses the washing machine's power each minute from the whole-house power. It is compared with 2 simple baselines and tested on a home it was not trained on. Scores: MAE, energy error, F1. Includes one actual-vs-predicted plot.
4. **Part 4** ([Recommendation.md](Recommendation.md)): one practical idea (move evening washes out of the 4–7 pm peak) with a way to measure it, the main limits (including UK → India), and what gets harder with 15/30-minute data.
5. **`sourcecode/main.py`**: runs Parts 1, 2 and 3 in one go.

## Folder layout

```
flock-refit/
  sourcecode/
    main.py             runs everything
    Section1.py         Part 1: clean raw House 1
    Section2.py         Part 2: washing-machine analysis
    Section3.py         Part 3: model
  plots/                the 5 plots shown in the .md files
  data/           >>>>> put the REFIT data files here (not uploaded: too big for GitHub) after downloading from
                        the official source (University of Strathclyde)
  DATA.md  
  README.md
  RESULTS.md
  Recommendation.md
  requirements.txt      Python packages needed
```

## How to run

### 1. Install

Tested with Python 3.14.

```
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # Mac / Linux
pip install -r requirements.txt
```

### 2. Get the data

The data files are too big for GitHub, so please download them and put them in a folder called `data/` inside the main flock-refit folder. Both downloads are `.7z` files; 7-Zip can open them.

⭐⭐⭐
Its important !! to make the data folder inside the main flock-refit folder and put the extracted csv files there , because the script will fetch data from directly there. 

- **Raw data** ([download](https://pureportal.strath.ac.uk/files/62090177/REFIT_RAW_081116.7z)): copy House 1's two files (Part1 and Part2) into `data/` and name them `RAW_House1_Part1.csv` and `RAW_House1_Part2.csv`.
- **Cleaned data** ([download](https://pureportal.strath.ac.uk/files/62090184/CLEAN_REFIT_081116.7z)): copy `CLEAN_House2.csv`, `CLEAN_House15.csv`, `CLEAN_House16.csv` and `CLEAN_House17.csv` into `data/`.

### 3. Run

From the `flock-refit` folder:

```
python sourcecode/main.py
```

- **Numbers** print in the terminal. These are the numbers used in the .md files.
- **Plots** are saved in `plots/`. The folder already has the plots used in the .md files, and running the code saves the same plots there again (it replaces them).
- **The first run is the slowest,** because it reads the big CSV files. Part 2 saves small `.pkl` copies in `data/`, so later runs are faster.
- **Each part can also run alone,** for example `python sourcecode/Section3.py`.
- **No plot windows open** (`SHOW1 = False` at the top of `Section1.py`, `SHOW = False` in `Section2.py` and `Section3.py`). Set it to `True` to see the plots while the code runs.

## Main choices, and why

### Assumptions

- **Time:** the `Unix` column is used everywhere (UTC). Part 1 stays in UTC. Parts 2 and 3 use UK local time, so "hour of day" matches the household clock.
- **Washing-machine column:** taken from the cleaned readme for each home. I skipped homes with a washer dryer, two washing machines, or a machine change.
- **A washing machine is "ON" above 20 W.** This value comes from Kelly & Knottenbelt (2015).
- **House 7 was dropped.** Its washing-machine channel showed power much more often than the others (22% of minutes vs 3–6%), so something else may have been plugged into the same monitor.

### Preprocessing

- **Part 1:** missing and impossible values become empty (NaN), not 0, because a 0 would look like "appliance off". Only gaps of 1–2 minutes are filled; longer gaps are flagged as outages. Duplicates: exact copies → keep one; same second but different values → keep the row that changed the most from the previous reading.
- **Parts 2 and 3:** readings are averaged to 1 minute, and empty minutes stay empty. The model is trained and scored only on minutes where both the whole-house and the washing-machine readings exist.

### Testing the model: leave one house out

- 4 rounds: train on 3 homes and test on the 4th, so each home is the test home once.
- **Why:** this matches the real use, where a utility wants to estimate washing-machine use in homes without a plug meter.
- **Why not random minutes:** minutes next to each other are almost the same. If they were split randomly, the model would "see the answer" in training and its score would look better than it really is.
- No data from the test home is used in training, not even for the baseline.

### Trade-offs

- **Gradient boosting instead of a neural network (like Seq2Point):** it's fast (a few seconds per round), handles missing values by itself, and is easy to explain. It may be less accurate.
- **The model looks at 15–60 minutes after each minute.** This gives better guesses, but it only works on past data (for example, yesterday's), not live.
- **Default model settings, no tuning:** the scores are fairer, but maybe not the best possible.
- **Model v2** (it adds 2 heating inputs) was added after seeing v1's results. It was the only change, and both versions are reported.
- **Only 4 homes:** quick to run and easy to explain, but the results may not hold for every home.

## AI tools used

- I used **Claude** (an AI assistant by Anthropic) to discuss options, explain ideas, draft and review code, and help write the .md files.
- I ran all the code myself on my computer, checked the outputs, and made the final choices. For example: dropping House 7, the "one heating = one wash" idea used in the wash rule and in model v2, and stopping model changes after v2.

## Possible improvements

1. **More homes:** the readme lists more homes with a plain washing-machine channel (Houses 3, 5, 6, 10, 11, 19, 20 and 21).
2. **Check the false alarms:** look at the dishwasher and tumble dryer channels at the times of false alarms to confirm the cause.
3. **Cold washes:** about 20% of washes in Houses 15 and 17 have no heating, and the model has little to go on for these.
4. **Two-step model:** first decide ON/OFF, then guess the power. This could reduce the "in-between" guesses.
5. **Try Seq2Point,** the neural network often used for this task in papers.
6. **A live version** that uses only past minutes.
7. **Test with 15- and 30-minute data,** to measure how much accuracy is lost.

## Data licence and references

- REFIT data is shared under the Creative Commons Attribution 4.0 licence. The readme asks users to cite Murray et al. (2015), *A data management platform for personalised real-time energy feedback* (EEDAL).
- The full reference lists are in [DATA.md](DATA.md), [RESULTS.md](RESULTS.md) and [Recommendation.md](Recommendation.md).
