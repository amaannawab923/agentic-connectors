import { useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Link2, Plus } from 'lucide-react';
import { useTheme } from '../../App';
import { useWorkflowStore } from '../../stores/workflowStore';
import { AgentNode, ConditionNode, InputNode, OutputNode, ParallelNode, MergeNode } from './nodes';

const nodeTypes = {
  agent: AgentNode,
  condition: ConditionNode,
  'if-else': ConditionNode,
  input: InputNode,
  output: OutputNode,
  parallel: ParallelNode,
  merge: MergeNode,
};

export function Canvas() {
  const { theme } = useTheme();
  const { fitView } = useReactFlow();

  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    setSelectedNodeId,
    showMinimap,
    addNode,
  } = useWorkflowStore();

  const onNodeClick = useCallback((event: React.MouseEvent, node: any) => {
    setSelectedNodeId(node.id);
  }, [setSelectedNodeId]);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, [setSelectedNodeId]);

  const handleAddInputNode = () => {
    const newNode = {
      id: `input-${Date.now()}`,
      type: 'input',
      position: { x: 250, y: 250 },
      data: {
        label: 'Workflow Input',
        variables: [
          { name: 'message', type: 'string' },
          { name: 'user_id', type: 'string' },
        ],
      },
    };
    addNode(newNode);
    setTimeout(() => fitView({ duration: 300 }), 100);
  };

  return (
    <div className="flex-1 relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        panOnScroll={true}
        selectionOnDrag={false}
        zoomOnScroll={true}
        zoomOnPinch={true}
        zoomOnDoubleClick={true}
        minZoom={0.25}
        maxZoom={2}
        connectionLineStyle={{ stroke: '#8B5CF6', strokeWidth: 2 }}
        defaultEdgeOptions={{ type: 'default', animated: false }}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        style={{
          backgroundColor: theme === 'dark' ? '#0A0F1C' : '#F8FAFC',
        }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={2}
          color={theme === 'dark' ? 'rgba(100, 116, 139, 0.3)' : 'rgba(148, 163, 184, 0.4)'}
        />

        {showMinimap && (
          <MiniMap
            position="bottom-right"
            style={{
              width: 150,
              height: 100,
              backgroundColor: theme === 'dark' ? 'rgba(30, 41, 59, 0.9)' : 'rgba(255, 255, 255, 0.9)',
              borderRadius: 8,
              border: `1px solid ${theme === 'dark' ? 'rgba(148, 163, 184, 0.1)' : '#E2E8F0'}`,
            }}
            maskColor={theme === 'dark' ? 'rgba(0, 0, 0, 0.5)' : 'rgba(0, 0, 0, 0.1)'}
          />
        )}

        <Controls
          position="bottom-left"
          style={{
            backgroundColor: theme === 'dark' ? '#1E293B' : '#FFFFFF',
            border: `1px solid ${theme === 'dark' ? 'rgba(148, 163, 184, 0.1)' : '#E2E8F0'}`,
            borderRadius: 8,
          }}
        />
      </ReactFlow>

      {/* Empty State */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-purple-500/20 to-blue-500/20 flex items-center justify-center">
              <Link2 className="w-10 h-10 text-purple-400" />
            </div>
            <h3 className={`text-lg font-medium mb-2 ${
              theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
            }`}>
              Start Building Your Workflow
            </h3>
            <p className="text-sm text-[#94A3B8] mb-6 max-w-sm">
              Drag nodes from the left panel onto the canvas, or click below to add your first node
            </p>
            <button
              onClick={handleAddInputNode}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm pointer-events-auto inline-flex items-center gap-2 shadow-lg shadow-purple-500/25"
            >
              <Plus className="w-4 h-4" />
              Add Input Node
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
