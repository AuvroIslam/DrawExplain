# DrawExplain results log

Measurements are made with the scripts in `backend/scripts/`: `eval_grounding.py` (drawing placement
against ground-truth boxes, IoU) and `eval_lessons.py` (real lessons on fixed pages, scored by automatic
fact checks). LLM output varies between runs, so single-run observations are marked as such. Run
outputs are written to `samples/eval/`.

## A misread figure (Pythagoras), found by a user test

A student asked "explain how we actually get the formula" on the Pythagoras picture, and the lesson said
the red square sits on the hypotenuse and two yellow squares on the legs (wrong: red 4x4 on the vertical
leg, yellow 3x3 on the bottom leg, the tilted 5x5 square on the hypotenuse). Diagnosis, cheapest first:
- Asked the model directly about the squares (original image, and original + marked image, 2 runs
  each): correct 4 of 4. So it is not a vision problem.
- Two fresh lessons: 1 of 2 wrong, and the wrong one reasoned from the text evidence. OCR read "α" as
  "a", read "β", missed "γ", so the model took "a, β" for the textbook legs a and b and placed the squares
  to match the convention instead of the picture. The region list gave no colours and no region for each
  big square (grid lines split them into cells), so nothing anchored "red on the left".
- Fix (general, not for this page): the region list now carries colours measured on the pixels
  ("R12 | shape | left | red"), and a prompt rule says to identify objects by what the image shows
  (position, colour, what they touch) and never by what a label letter usually means.
- After the fix, the same question: 3 of 3 lessons correct (left red 4x4 = 16, bottom yellow 3x3 = 9,
  tilted 5x5 = 25 on the hypotenuse, 16 + 9 = 25).
- Regression, 1 run each (L5): Dijkstra, TCP, flowchart, BFS/DFS, quadratic and Pythagoras 5/5. The SJF
  chart first ran without its solver: the extraction (now also reading the drawn run order) took 12.9 s
  and the lesson stopped waiting at 12 s. The wait is now 20 s; rerun 4/5 with every waiting time and the
  2.36 average right (the miss: it wrote "P12 waits 13 -> 21" without the number 8).
