import { useCallback } from 'react';
import { ReactFlowProvider, useReactFlow } from '@xyflow/react';
import { BuilderHeader } from './BuilderHeader';
import { NodePalette } from './NodePalette';
import { Canvas } from './Canvas';
import { ConfigPanel } from './ConfigPanel';
import { Toolbar } from './Toolbar';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';
import '@xyflow/react/dist/style.css';

function WorkflowBuilderInner({ onBack }: { onBack: () => void }) {
  const { fitView, zoomIn, zoomOut, screenToFlowPosition } = useReactFlow();

  const {
    name,
    nodes,
    addNode,
    undo,
    redo,
    past,
    future,
    saveStatus,
    showMinimap,
    toggleMinimap,
    deleteSelectedNodes,
    setSelectedNodeId,
    setSaveStatus,
  } = useWorkflowStore();

  let nodeIdCounter = 0;
  const getId = () => `node-${Date.now()}-${nodeIdCounter++}`;

  // Keyboard shortcuts
  useKeyboardShortcuts({
    onSave: handleSave,
    onUndo: undo,
    onRedo: redo,
    onDelete: deleteSelectedNodes,
    onEscape: () => setSelectedNodeId(null),
    onFitView: () => fitView({ duration: 300 }),
  });

  // Drag and drop handlers
  const onDragStart = (event: React.DragEvent, type: string, data: any) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({ type, data }));
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const reactFlowBounds = (event.target as HTMLElement).getBoundingClientRect();
      const transferData = event.dataTransfer.getData('application/reactflow');

      if (!transferData) return;

      const { type, data } = JSON.parse(transferData);
      const position = screenToFlowPosition({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      let newNode: any = {
        id: getId(),
        position,
        data: {},
      };

      // Configure node based on type
      if (type === 'agent') {
        newNode = {
          ...newNode,
          type: 'agent',
          data: {
            label: data.name,
            description: data.description,
            icon: data.icon,
            status: 'idle',
            inputs: data.parameters,
            outputs: data.outputs,
            agentId: data.id,
          },
        };
      } else if (type === 'input') {
        newNode = {
          ...newNode,
          type: 'input',
          data: {
            label: 'Workflow Input',
            variables: [
              { name: 'message', type: 'string' },
              { name: 'user_id', type: 'string' },
            ],
          },
        };
      } else if (type === 'output') {
        newNode = {
          ...newNode,
          type: 'output',
          data: {
            label: 'Workflow Output',
            variables: [
              { name: 'response', type: 'string' },
            ],
          },
        };
      } else if (type === 'if-else') {
        newNode = {
          ...newNode,
          type: 'condition',
          data: {
            label: 'Condition',
            condition: '{{input.value}} == true',
            branches: ['if', 'else'],
          },
        };
      } else if (type === 'parallel') {
        newNode = {
          ...newNode,
          type: 'parallel',
          data: {
            label: 'Parallel Split',
            branches: 3,
          },
        };
      } else if (type === 'merge') {
        newNode = {
          ...newNode,
          type: 'merge',
          data: {
            label: 'Merge',
            inputCount: 3,
            strategy: 'Wait All',
          },
        };
      }

      addNode(newNode);
    },
    [screenToFlowPosition, addNode]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  function handleSave() {
    setSaveStatus('saving');
    setTimeout(() => {
      setSaveStatus('saved');
      console.log('Workflow saved:', { nodes, edges: useWorkflowStore.getState().edges });
    }, 500);
  }

  function handleTest() {
    alert('Test run functionality would be implemented here');
  }

  function handlePublish() {
    alert('Publish functionality would be implemented here');
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <BuilderHeader
        workflowName={name}
        workflowIcon="🔄"
        onBack={onBack}
        onSave={handleSave}
        onTest={handleTest}
        onPublish={handlePublish}
      />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden" onDrop={onDrop} onDragOver={onDragOver}>
        <NodePalette onDragStart={onDragStart} />
        <Canvas />
        <ConfigPanel />
      </div>

      {/* Toolbar */}
      <Toolbar
        onZoomIn={() => zoomIn()}
        onZoomOut={() => zoomOut()}
        onFitView={() => fitView({ duration: 300 })}
        onUndo={undo}
        onRedo={redo}
        canUndo={past.length > 0}
        canRedo={future.length > 0}
        saveStatus={saveStatus}
        nodeCount={nodes.length}
        showMinimap={showMinimap}
        onToggleMinimap={toggleMinimap}
      />
    </div>
  );
}

export function WorkflowBuilder({ onBack }: { onBack: () => void }) {
  return (
    <ReactFlowProvider>
      <WorkflowBuilderInner onBack={onBack} />
    </ReactFlowProvider>
  );
}
