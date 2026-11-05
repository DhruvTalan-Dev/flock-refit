import time

import Section1   # Part 1: clean raw House 1
import Section2   # Part 2: washing-machine analysis
import Section3   # Part 3: disaggregation model


def main():
    parts = [("PART 1: CLEANING RAW HOUSE 1", Section1),
             ("PART 2: WASHING-MACHINE ANALYSIS", Section2),
             ("PART 3: DISAGGREGATION MODEL", Section3)]
    for name, part in parts:
        print("#" * 40)
        print(name)
        print("#" * 40)
        t0 = time.time()
        part.run()
        print(f"{name} done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()