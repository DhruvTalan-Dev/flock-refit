# Recommendation.md: utility summary and Part 4 answers

The numbers here come from RESULTS.md (Parts 2 and 3) and DATA.md (Part 1). Outside facts are listed in the References at the end.

---

## Summary for the utility: finding washing-machine use from whole-house power

**What we built:** a model that guesses the washing machine's power every minute using only the whole-house meter (1-minute data). It was tested on 4 UK homes (REFIT cleaned data, Houses 2, 15, 16 and 17), each time on a home it had never seen in training.

**What the model is good for**
- **Finding when washes happen.** F1 is 0.32–0.75 in unseen homes, better than both simple baselines (0.14 or less) in all 4 homes.
- That gives a **rough picture of each home's wash habits** (usual start time), which is enough to **pick homes for a targeted tip** (4.1).

**What it is not good for (yet)**
- **Washing-machine kWh** for a home or a bill: the energy error is −62% to +98%.
- **Homes with other ~2 kW heating appliances** (dishwasher, tumble dryer, heaters): these cause false alarms (precision 0.20–0.25 in 3 of 4 homes).
- **Live use:** the model looks up to 60 minutes after each minute, so it only works on past data (for example, yesterday's).
- **15/30-minute meter data, or machines that wash in cold water** (4.2 d and 4.3).

**Before wider use:** test on many more homes (only 4 here), and retrain on local data (for example, Indian homes).

---

## Part 4 answers

### 4.1 Idea: move evening washes out of the peak

**The idea**
- Use the model on smart-meter data to find homes that often start a wash in the evening peak (4–7 pm in the UK [1]).
- Send only those homes a short tip: "Start your wash before 4 pm or after 7 pm. Many machines have a delay timer." This can go with a time-of-use tariff, where power is cheaper outside the peak.
- The tip does **not** suggest overnight washes, because UK fire services advise against leaving washing machines running overnight [2].

**Why our analysis supports it**
1. **A wash is a big load:** each wash heats water at about 2 kW for 20–35 minutes (RESULTS.md 2.3).
2. **Homes have habits:** the busiest start hour has 2–3 times the even share (RESULTS.md 2.4). House 16 starts most of its washes at 18:00, inside the peak.
3. **It needs "when", not "how much":** the model finds when washes run (F1 0.32–0.75), but its energy totals are not reliable (−62% to +98%) (RESULTS.md 3.6).
4. **Honest note:** moving a wash doesn't cut total kWh. It lowers evening demand for the utility and the bill for the customer.

**How to measure if it worked**
1. **Pick homes** where the model finds peak-time washes often, for example 4 or more a month (our choice). A home flagged only once may be a false alarm (RESULTS.md 3.8).
2. **Split them by chance:** half get the tip, half get nothing (the control group).
3. **Compare 3 months before with 3 months after**, in both groups:
   - **Main measure:** % of washes starting at 4–7 pm, found by the model.
   - **Second check:** average household power at 4–7 pm, read straight from the smart meter. This needs no model, so the model's errors can't affect it.
4. **Effect** = drop in the tip group − drop in the control group.

| (made-up numbers) | Before | After | Change |
|---|---|---|---|
| Tip group | 40% | 25% | −15 points |
| Control group | 40% | 38% | −2 points |
| **Effect of the tip** | | | **−13 points** |

- **Why a control group:** seasons and holidays also change habits. The control group shows that normal change.
- **Why model errors matter less here:** homes are split by chance and both groups are measured by the same model, so false alarms should affect both groups about the same.

### 4.2 Limits

**a. Overlapping appliance signatures**
- Any appliance that heats at about 2 kW for 10+ minutes (a dishwasher, tumble dryer or electric heater) looks like washing-machine heating in the whole-house power. This is the main cause of false alarms (precision only 0.20–0.25 in Houses 2, 16 and 17) and of energy totals that are too high (+10% to +98%) (RESULTS.md 3.6, 3.8).
- Two appliances at once (for example, the kettle during heating) can also hide a wash.
- **Effect on the idea:** some homes will get the tip by mistake. The harm is small (one message), and the "4 or more a month" filter and the meter check from 4.1 help.

**b. Missing data**
- The washing-machine channel is missing 6–25% of minutes. REFIT also set long gaps to 0, so some "off" minutes may really be missing (RESULTS.md 2.2). In House 1's raw data, 13% of minutes were outages (DATA.md).
- Gaps leave fewer washes to judge a home by, so a utility should only flag homes with enough data (for example, 80% or more of the month; our choice).

**c. Household differences**
- Each house has its own machine, wash day and wash length (median 62–97 min) (RESULTS.md 2.4, 2.5). In a house the model hasn't seen, F1 ranges from 0.32 to 0.75, so results change a lot from home to home.
- We used only 4 houses and 4 machines, so the numbers are not proof for a large population.

**d. Applying UK results to India**
- **Machines are different:** top-load machines had the largest share of the Indian market in 2025, about 68% [3], and buying guides say most top-loaders have no built-in heater and wash in cold water [4]. Our model relies on the ~2 kW heating block, so it would miss many Indian washes. It would need retraining on Indian data, which would also teach it Indian wash habits.
- **Other big loads:** electric water heaters (geysers, usually about 2 kW) and ACs are common. They could look like washing-machine heating and cause more false alarms.
- **Cheap hours are different:** under India's Time-of-Day rules, power in the solar hours (8 hours during the day) must cost at least 20% less than the normal tariff [5, 6]. So in India, the tip from 4.1 should move washes **into daytime solar hours**. Rollout depends on smart meters: a draft amendment proposes April 2028 as the deadline for households [6].

### 4.3 What gets harder with only 15- or 30-minute data

Each 15- or 30-minute reading is an average, so short and detailed shapes disappear. A 3-minute kettle at 3 kW becomes only about 300 W in a 30-minute slot. A wash's heating block (about 2 kW for 20–35 minutes) can be split across two slots at about 1 kW each, which looks much like a 15-minute dishwasher block. Most of our model's inputs need 1-minute data: the jump from one minute to the next (`diff`), the bumpy rinse and spin (`std_30`), and the "1,500 W for 5+ minutes" heating rule (`heat_now`). The low-power part of a wash (100–500 W) would mostly disappear into the base load, and a typical wash (median 62–97 minutes) would be only about 3–5 half-hour readings. So the model could no longer reliably say when a wash starts or ends, or tell it apart from other ~2 kW appliances. At best it could say "a big heating load probably ran in this half hour." For the idea in 4.1, the main measure (counting peak-time washes) becomes much weaker. The second check, average household power at 4–7 pm, still works: the peak is six half-hour readings, and that check needs no model.

---

## References

1. University of Warwick, Sustainability news (2017): early evening (4–7 pm) is the UK peak for energy use. https://warwick.ac.uk/sustainability/news/triad_2017
2. London Fire Brigade (2022), white goods safety advice: don't run washing machines, dishwashers or tumble dryers overnight. https://london-fire.gov.uk/incidents/2022/february/flat-fire-pinner
3. Mordor Intelligence, India Washing Machine Market report (via GII Research). https://www.giiresearch.com/report/moi2124658-india-washing-machine-market-share-analysis.html
4. ReadThisFirst, washing machine buying guide (India), April 2026. A buying guide, not a research source. https://readthisfirst.in/?p=238
5. Lok Sabha answer on the Electricity (Rights of Consumers) Amendment Rules, 2023 (Time-of-Day tariff). https://eparlib.nic.in/bitstream/123456789/2504104/1/AU41.pdf
6. Zerodha Daily Brief, "The new rules of paying for electricity" (Time-of-Day rules and the draft amendment). https://thedailybrief.zerodha.com/p/the-new-rules-of-paying-for-electricity
