# StudyLens Live Whiteboard (Devpost write-up, < 500 words)

## Inspiration
Stuck on a lecture slide, we paste it into a chatbot and get a wall of text that never points at
anything. A teacher would walk to the board, circle the router, draw the arrow and write the numbers
in. Earlier "AI draws on your screen" experiments failed for one reason: the model's coordinates are
almost right, so circles miss and labels cover the text.

## What it does
Upload a slide, a phone photo of a textbook page or a PDF lecture. StudyLens teaches it by drawing on
top of the untouched page: circles, arrows, word-level underlines and handwritten notes appear the
moment the narrator says them. On an algorithm slide it runs the algorithm. On Dijkstra it writes
"dist = 0", "1 + 3 = 4" next to the nodes. Circle a confusing part with the pen and ask why; it draws
the answer. A tap-on-the-image quiz closes the lesson.

## How we built it
The language model never draws. CV finds the regions first. RapidOCR reads text lines and word
spans. A rescue pass reads lone labels the detector misses, like graph weights. OpenCV finds shapes
as holes in a colour-edge map. Phone photos are flattened with a homography. Every region is tagged
on a Set-of-Mark image. gpt-5.5 plans the lesson as strict JSON and, per drawing, returns region ids
plus its own box estimate. A fusion step cross-checks the two signals per target. Self-consistency
gating measures how far each response's estimates can be trusted. A geometry engine pads ellipses,
lands arrows on box edges and puts labels in free space. The frontend is an Excalidraw board
animating marker strokes in sync with ElevenLabs word timestamps. Steps stream to the board as soon
as each is grounded.

## Challenges
- Lone digits and letters: the OCR detector proposes text lines, so graph edge weights vanished. We
  added a recognizer-only rescue pass over character-sized ink blobs.
- Connector lines fused separate boxes into one shape, and empty pockets between edges looked like
  shapes. Colour-edge holes plus a "border cuts other shapes" test fixed both.
- Our first fusion trusted gpt-4.1-mini's noisy box estimates and lost to plain region ids. Measuring
  each response's self-consistency fixed it: 63% to 81% tight hits.

## Accomplishments
We measured placement on 407 ground-truth targets in 24 images. Raw GPT coordinates land tightly
(IoU >= 0.75) 34% of the time with gpt-5.4-mini and 0% with gpt-4.1-mini. Our grounding reaches 83%
and 81%. A cheap model draws as precisely as the newest one.

## What we learned
The newest models localize well on clean, sparse slides (0.95 IoU in our first probe). The gap opens
on dense diagrams, photos and small text, and that is real coursework. Good teaching also needs
"teach by doing": gpt-5.5 traced Dijkstra correctly where a smaller model guessed.

## What's next
Margin sketches drawn via Mermaid, formula OCR to LaTeX, and lessons saved as annotated study
sheets.
