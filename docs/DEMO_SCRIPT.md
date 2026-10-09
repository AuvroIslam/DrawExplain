# 3-minute demo video: shot list and voice-over

Hard limit: 3:00. Record at 1440x900 or 1920x1080, browser zoom 100%, cursor visible.

## Before recording
1. Start the backend with the cache on, so the lessons you already generated replay instantly:
   `cd backend && set LLM_CACHE=1 && .venv\Scripts\python -m uvicorn app.main:app --port 8000`
   (Git Bash: `LLM_CACHE=1 .venv/Scripts/python -m uvicorn app.main:app --port 8000`)
2. `cd frontend && npm run dev`, then open http://localhost:5173.
3. Do one full dry run of every shot. That warms the OCR models, the LLM cache and the voice cache,
   so the take has no waiting.
4. Have ready: `dijkstra-slides.pdf` (page 3), one phone photo of a textbook page, and the TCP slide
   (`samples/real/tcp_lost_segment.png`).
5. Voice: ElevenLabs. Volume on. Close notifications.

## Shots

| Time | Screen | Voice-over |
|---|---|---|
| 0:00-0:12 | The Dijkstra slide next to a chatbot's wall-of-text answer | "When a slide doesn't make sense, a chatbot gives you a wall of text. A teacher would walk to the board and *show* you." |
| 0:12-0:20 | StudyLens landing page, drop `dijkstra-slides.pdf`, pick page 3 | "StudyLens is that teacher. I drop in my lecture PDF and pick the slide." |
| 0:20-0:30 | Scanning animation, "Found 49 things on this page", click **Teach me this** | "First it reads the page with computer vision: every node, edge weight and line of text." |
| 0:30-1:15 | The lesson plays: circles, arrows, "dist = 0", "1 + 3 = 4" appear as the voice speaks | Let the tutor's own narration play (cut between steps if needed). |
| 1:15-1:35 | Draw a circle around node G with the pen, type "Why did G change from 9 to 4?" | "I'm still not sure about G, so I circle it and ask." (Let the purple answer play.) |
| 1:35-1:50 | Quiz: tap the wrong node once, then the right one | "And it checks I understood, by tapping the picture." |
| 1:50-2:25 | Toggle **How it sees**: region tags R1..Rn, grounding badges, timings | "Here's the trick. The language model never draws. Computer vision finds every region first; the model plans the lesson by choosing region IDs and giving its own box estimate; we cross-check the two before anything is drawn." |
| 2:25-2:40 | The evaluation chart (`samples/eval/chart_hit75.png`) | "On 407 targets, raw GPT coordinates land tightly 34% of the time. Ours land 83%, and even an older, cheaper model hits 81%." |
| 2:40-2:52 | Quick cut: a phone photo of a textbook page gets flattened and taught, then the TCP lost-segment slide | "It works on phone photos and on any subject." |
| 2:52-3:00 | Logo + GitHub URL | "StudyLens: a tutor that teaches by drawing." |

## Tips
- If a lesson takes a while live, cut the wait: the video is judged on the result, and the README
  explains streaming.
- Keep the mouse still while the tutor draws; the drawings are the star.
- Upload: YouTube, public, <= 3:00, then paste the link into the Devpost form and the README.
