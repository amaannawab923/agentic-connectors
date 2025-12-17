import React from 'react';
import { EdgeProps, getSmoothStepPath, EdgeLabelRenderer, BaseEdge } from 'reactflow';
import { X } from 'lucide-react';

export function CustomEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  selected,
  data,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const onDelete = () => {
    if (data?.onDelete) {
      data.onDelete(id);
    }
  };

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      {selected && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
          >
            <button
              onClick={onDelete}
              className="w-6 h-6 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center cursor-pointer shadow-lg transition-colors"
              title="Delete connection"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}