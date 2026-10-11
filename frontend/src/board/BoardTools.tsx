// The board's own toolbar (lucide icons) in place of Excalidraw's built-in one: pick a tool for the
// student's pen, undo/redo, and clear the student's drawings. Tutor drawings are never touched.
import {
  Circle,
  Eraser,
  Hand,
  type LucideIcon,
  MousePointer2,
  MoveUpRight,
  Pencil,
  Redo2,
  Square,
  Trash2,
  Type,
  Undo2,
} from "lucide-react";

export type ToolType = "selection" | "freedraw" | "ellipse" | "rectangle" | "arrow" | "text" | "eraser" | "hand";

const TOOLS: { type: ToolType; label: string; key: string; Glyph: LucideIcon }[] = [
  { type: "selection", label: "Select", key: "V", Glyph: MousePointer2 },
  { type: "freedraw", label: "Pen", key: "P", Glyph: Pencil },
  { type: "ellipse", label: "Circle", key: "O", Glyph: Circle },
  { type: "rectangle", label: "Box", key: "R", Glyph: Square },
  { type: "arrow", label: "Arrow", key: "A", Glyph: MoveUpRight },
  { type: "text", label: "Text", key: "T", Glyph: Type },
  { type: "eraser", label: "Eraser", key: "E", Glyph: Eraser },
  { type: "hand", label: "Move the page", key: "H", Glyph: Hand },
];

interface Props {
  active: string;
  onTool: (type: ToolType) => void;
  onUndo: () => void;
  onRedo: () => void;
  onClear: () => void;
}

export function BoardTools({ active, onTool, onUndo, onRedo, onClear }: Props) {
  return (
    <div className="board-tools" role="toolbar" aria-label="Drawing tools">
      {TOOLS.map(({ type, label, key, Glyph }) => (
        <button
          key={type}
          type="button"
          className={`board-tool${active === type ? " on" : ""}`}
          aria-pressed={active === type}
          title={`${label} (${key})`}
          onClick={() => onTool(type)}
        >
          <Glyph size={18} strokeWidth={2} aria-hidden="true" />
        </button>
      ))}
      <span className="board-tools-divider" aria-hidden="true" />
      <button type="button" className="board-tool" title="Undo (Ctrl+Z)" onClick={onUndo}>
        <Undo2 size={18} strokeWidth={2} aria-hidden="true" />
      </button>
      <button type="button" className="board-tool" title="Redo (Ctrl+Y)" onClick={onRedo}>
        <Redo2 size={18} strokeWidth={2} aria-hidden="true" />
      </button>
      <button type="button" className="board-tool" title="Clear my drawings" onClick={onClear}>
        <Trash2 size={18} strokeWidth={2} aria-hidden="true" />
      </button>
    </div>
  );
}
