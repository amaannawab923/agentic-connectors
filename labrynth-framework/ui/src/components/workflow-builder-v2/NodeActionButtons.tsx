import React from 'react';
import { Circle, Copy, RotateCcw, Trash2, ArrowUpDown } from 'lucide-react';

interface NodeActionButtonsProps {
  nodeId: string;
  nodePosition: { x: number; y: number };
  portOrientation: string;
  onDelete: (nodeId: string) => void;
  onTogglePortOrientation: (nodeId: string) => void;
  isDark: boolean;
  viewport: { x: number; y: number; zoom: number };
}

export function NodeActionButtons({ nodeId, nodePosition, portOrientation, onDelete, onTogglePortOrientation, isDark, viewport }: NodeActionButtonsProps) {
  // Convert flow coordinates to screen coordinates
  const screenX = nodePosition.x * viewport.zoom + viewport.x;
  const screenY = nodePosition.y * viewport.zoom + viewport.y - 60; // 60px above the node

  return (
    <div
      className={`absolute flex items-center gap-2 ${isDark ? 'bg-[#1a1a1a] border-gray-700' : 'bg-white border-gray-300'} border rounded-lg shadow-lg p-1.5 pointer-events-auto`}
      style={{
        left: `${screenX}px`,
        top: `${screenY}px`,
        zIndex: 1000,
      }}
    >
      <button
        className={`p-2 ${isDark ? 'bg-[#2a2a2a] hover:bg-[#333333]' : 'bg-gray-200 hover:bg-gray-300'} rounded transition-colors`}
        title="Run block"
      >
        <Circle className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
      </button>
      <button
        className={`p-2 ${isDark ? 'bg-[#2a2a2a] hover:bg-[#333333]' : 'bg-gray-200 hover:bg-gray-300'} rounded transition-colors`}
        title="Duplicate block"
      >
        <Copy className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
      </button>
      <button
        onClick={() => onTogglePortOrientation(nodeId)}
        className={`p-2 ${portOrientation === 'vertical' ? 'bg-blue-500 hover:bg-blue-600' : `${isDark ? 'bg-[#2a2a2a] hover:bg-blue-500' : 'bg-gray-200 hover:bg-blue-400'}`} rounded transition-colors group`}
        title={portOrientation === 'vertical' ? 'Switch to Horizontal Ports' : 'Switch to Vertical Ports'}
      >
        <ArrowUpDown className={`w-4 h-4 ${portOrientation === 'vertical' ? 'text-white' : `${isDark ? 'text-gray-400 group-hover:text-white' : 'text-gray-600 group-hover:text-white'}`}`} />
      </button>
      <button
        onClick={() => onDelete(nodeId)}
        className={`p-2 ${isDark ? 'bg-[#2a2a2a] hover:bg-red-600' : 'bg-gray-200 hover:bg-red-500'} rounded transition-colors group`}
        title="Delete block"
      >
        <Trash2 className={`w-4 h-4 ${isDark ? 'text-gray-400 group-hover:text-white' : 'text-gray-600 group-hover:text-white'}`} />
      </button>
    </div>
  );
}