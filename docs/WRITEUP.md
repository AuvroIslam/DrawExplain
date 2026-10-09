# StudyLens Live Whiteboard (Devpost write-up, < 500 words)

## Inspiration
Stuck on a lecture slide, we paste it into a chatbot and get a wall of text that never points at
anything. A teacher would walk to the board, circle the router, draw the arrow and write the numbers
in. Earlier "AI draws on your screen" experiments failed because the model's coordinates are almost
right: circles miss and labels cover the text.

## What it does
Upload a slide, a phone photo of a textbook page or a PDF lecture (read it like a book, press Explain
on any page, with or without your own question). StudyLens teaches by drawing on the untouched page:
circles, arrows, word-level underlines and handwritten values appear the moment the narrator says them.
On an algorithm slide it runs the algorithm: on Dijkstra it writes "B ∞→5", "G 9→4" next to the nodes,
in the real relaxation order. Circle a confusing part and ask why; it draws the answer. A tap quiz
closes the lesson.

## How we built it
The language model never draws and never does the arithmetic. CV finds the regions first: RapidOCR
lines and word spans, a rescue pass for lone labels like graph weights, OpenCV shapes as holes in a
colour-edge map, a homography for phone photos, all tagged on a Set-of-Mark image. gpt-5.5 plans the
lesson as strict JSON with region ids plus its own box per drawing; fusion cross-checks the two, gated
by each response's self-consistency; a geometry engine places ellipses, arrows and labels. On an
algorithm page the model only reads the problem (graph, process table, reference string), the pixels
check the reading and code runs it: Dijkstra, BFS/DFS, Prim/Kruskal, sorts, binary search, TCP
congestion control, CPU scheduling, page replacement. An optional GPU service on Modal adds SAM 2.1 for
uncertain targets and formula OCR to LaTeX. The board is Excalidraw, synced to ElevenLabs timestamps.

## Challenges
- Graph weights vanished from OCR; a recognizer-only rescue pass over character-sized blobs fixed it.
- Our first fusion trusted gpt-4.1-mini's noisy boxes; measuring self-consistency fixed it (63% to 81%
  tight hits).
- "Simulate Dijkstra" prompts still skipped relaxations; running it in code did not.

## Accomplishments
- Placement: on 407 ground-truth targets, raw GPT coordinates land tightly (IoU >= 0.75) 34% of the
  time; our grounding reaches 83%. SAM lifts the uncertain ones from 26% to 47%.
- Teaching: fact-checked real lessons on 20 pages (17 from Wikimedia Commons). Hard algorithm pages:
  fully correct runs 3/9 with prompting, 9/9 with code-run simulations; all 20 pages: 0.86 to 0.93.

## What we learned
Models localize well on clean slides; the gap opens on dense diagrams, photos and small text. Reading
is easier than computing: the model reads a graph reliably, but only code relaxes every edge. The
remaining errors are reading errors, fixable the same way: let the pixels check what the model read.

## What's next
Handwriting, more solvers (deadlock detection, recursion), lessons saved as annotated study sheets.
