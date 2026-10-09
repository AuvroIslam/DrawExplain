# StudyLens frontend

React 19 + TypeScript + Vite app for StudyLens Live Whiteboard. See the root [README](../README.md)
for the project, and [CONTRACT.md](../CONTRACT.md) for the API it talks to.

```bash
npm install
npm run dev      # http://localhost:5173, proxies /api to the backend on :8000
npm run build    # type-check + production build
```

- `src/board/`: the whiteboard engine on [Excalidraw](https://github.com/excalidraw/excalidraw):
  tutor annotations become freedraw/arrow/text elements animated like a marker; overlays for
  "How it sees"; quiz taps; PNG export.
- `src/player/`: lesson playback, cue timing from ElevenLabs word timestamps or the browser voice.
- `src/hooks/useStudySession.ts`: upload (images and PDF pages), streamed lessons, follow-ups, quiz.
- `?mock=1` runs the whole UI on bundled sample data without the backend.
