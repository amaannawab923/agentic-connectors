import { Minus, Plus, Maximize2, Undo2, Redo2, Check, Loader2, AlertCircle, Map } from 'lucide-react';
import { useTheme } from '../../App';

interface ToolbarProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitView: () => void;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  saveStatus: 'idle' | 'saving' | 'saved' | 'error';
  nodeCount: number;
  showMinimap: boolean;
  onToggleMinimap: () => void;
}

export function Toolbar({
  onZoomIn,
  onZoomOut,
  onFitView,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  saveStatus,
  nodeCount,
  showMinimap,
  onToggleMinimap,
}: ToolbarProps) {
  const { theme } = useTheme();

  return (
    <div className={`h-12 flex items-center justify-between px-4 border-t ${
      theme === 'dark'
        ? 'bg-[#0F172A] border-[rgba(148,163,184,0.1)]'
        : 'bg-white border-[#E2E8F0]'
    }`}>
      {/* Left: Zoom Controls */}
      <div className="flex items-center gap-1">
        <button
          onClick={onZoomOut}
          className={`p-2 rounded-lg transition-colors ${
            theme === 'dark'
              ? 'text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)]'
              : 'text-[#64748B] hover:bg-[#F9FAFB]'
          }`}
          title="Zoom Out"
        >
          <Minus className="w-4 h-4" />
        </button>
        <button
          onClick={onZoomIn}
          className={`p-2 rounded-lg transition-colors ${
            theme === 'dark'
              ? 'text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)]'
              : 'text-[#64748B] hover:bg-[#F9FAFB]'
          }`}
          title="Zoom In"
        >
          <Plus className="w-4 h-4" />
        </button>
        <button
          onClick={onFitView}
          className={`p-2 rounded-lg transition-colors ${
            theme === 'dark'
              ? 'text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)]'
              : 'text-[#64748B] hover:bg-[#F9FAFB]'
          }`}
          title="Fit View"
        >
          <Maximize2 className="w-4 h-4" />
        </button>

        <div className={`w-px h-6 mx-2 ${
          theme === 'dark' ? 'bg-[rgba(148,163,184,0.1)]' : 'bg-[#E2E8F0]'
        }`} />

        <button
          onClick={onUndo}
          disabled={!canUndo}
          className={`p-2 rounded-lg transition-colors ${
            canUndo
              ? theme === 'dark'
                ? 'text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)]'
                : 'text-[#64748B] hover:bg-[#F9FAFB]'
              : 'text-[#64748B] opacity-30 cursor-not-allowed'
          }`}
          title="Undo (Cmd+Z)"
        >
          <Undo2 className="w-4 h-4" />
        </button>
        <button
          onClick={onRedo}
          disabled={!canRedo}
          className={`p-2 rounded-lg transition-colors ${
            canRedo
              ? theme === 'dark'
                ? 'text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)]'
                : 'text-[#64748B] hover:bg-[#F9FAFB]'
              : 'text-[#64748B] opacity-30 cursor-not-allowed'
          }`}
          title="Redo (Cmd+Shift+Z)"
        >
          <Redo2 className="w-4 h-4" />
        </button>
      </div>

      {/* Center: Save Status */}
      <div className="flex items-center gap-4">
        <span className={`text-xs flex items-center gap-1.5 ${
          saveStatus === 'saved' ? 'text-green-400' :
          saveStatus === 'saving' ? 'text-[#94A3B8]' :
          saveStatus === 'error' ? 'text-red-400' :
          'text-[#64748B]'
        }`}>
          {saveStatus === 'saved' && <><Check className="w-3 h-3" /> Saved</>}
          {saveStatus === 'saving' && <><Loader2 className="w-3 h-3 animate-spin" /> Saving...</>}
          {saveStatus === 'error' && <><AlertCircle className="w-3 h-3" /> Save failed</>}
          {saveStatus === 'idle' && <>Auto-save</>}
        </span>

        <span className="text-xs text-[#64748B]">
          Nodes: {nodeCount}
        </span>
      </div>

      {/* Right: Toggle Controls */}
      <div className="flex items-center gap-1">
        <button
          onClick={onToggleMinimap}
          className={`p-2 rounded-lg transition-colors ${
            showMinimap
              ? theme === 'dark'
                ? 'bg-[rgba(139,92,246,0.2)] text-purple-400'
                : 'bg-purple-100 text-purple-600'
              : theme === 'dark'
                ? 'text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)]'
                : 'text-[#64748B] hover:bg-[#F9FAFB]'
          }`}
          title="Toggle Minimap"
        >
          <Map className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
