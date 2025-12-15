import { create } from 'zustand';
import { Node, Edge, Connection, addEdge, applyNodeChanges, applyEdgeChanges } from '@xyflow/react';

interface WorkflowState {
  // Workflow metadata
  id: string | null;
  name: string;
  description: string;

  // Graph data
  nodes: Node[];
  edges: Edge[];

  // Selection
  selectedNodeId: string | null;

  // History (for undo/redo)
  past: { nodes: Node[]; edges: Edge[] }[];
  future: { nodes: Node[]; edges: Edge[] }[];

  // Save status
  saveStatus: 'idle' | 'saving' | 'saved' | 'error';
  lastSaved: Date | null;

  // UI state
  showMinimap: boolean;
  showVariables: boolean;

  // Actions
  setWorkflow: (workflow: { id: string; name: string; description: string; nodes: Node[]; edges: Edge[] }) => void;
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  onNodesChange: (changes: any) => void;
  onEdgesChange: (changes: any) => void;
  onConnect: (connection: Connection) => void;
  addNode: (node: Node) => void;
  updateNode: (nodeId: string, data: Partial<any>) => void;
  deleteNode: (nodeId: string) => void;
  deleteSelectedNodes: () => void;
  setSelectedNodeId: (id: string | null) => void;
  undo: () => void;
  redo: () => void;
  saveSnapshot: () => void;
  setSaveStatus: (status: 'idle' | 'saving' | 'saved' | 'error') => void;
  toggleMinimap: () => void;
  toggleVariables: () => void;
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  // Initial state
  id: null,
  name: 'Untitled Workflow',
  description: '',
  nodes: [],
  edges: [],
  selectedNodeId: null,
  past: [],
  future: [],
  saveStatus: 'idle',
  lastSaved: null,
  showMinimap: true,
  showVariables: false,

  // Actions
  setWorkflow: (workflow) => set({
    id: workflow.id,
    name: workflow.name,
    description: workflow.description,
    nodes: workflow.nodes,
    edges: workflow.edges,
  }),

  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),

  onNodesChange: (changes) => {
    set({ nodes: applyNodeChanges(changes, get().nodes) });
  },

  onEdgesChange: (changes) => {
    set({ edges: applyEdgeChanges(changes, get().edges) });
  },

  onConnect: (connection) => {
    get().saveSnapshot();
    set({ edges: addEdge(connection, get().edges) });
  },

  addNode: (node) => {
    get().saveSnapshot();
    set({ nodes: [...get().nodes, node], selectedNodeId: node.id });
  },

  updateNode: (nodeId, data) => {
    set({
      nodes: get().nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      ),
    });
  },

  deleteNode: (nodeId) => {
    get().saveSnapshot();
    set({
      nodes: get().nodes.filter((n) => n.id !== nodeId),
      edges: get().edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      selectedNodeId: null,
    });
  },

  deleteSelectedNodes: () => {
    const { selectedNodeId } = get();
    if (selectedNodeId) {
      get().deleteNode(selectedNodeId);
    }
  },

  setSelectedNodeId: (id) => set({ selectedNodeId: id }),

  saveSnapshot: () => {
    const { nodes, edges, past } = get();
    set({
      past: [...past.slice(-50), { nodes, edges }],
      future: [],
    });
  },

  undo: () => {
    const { past, nodes, edges, future } = get();
    if (past.length === 0) return;

    const previous = past[past.length - 1];
    set({
      nodes: previous.nodes,
      edges: previous.edges,
      past: past.slice(0, -1),
      future: [{ nodes, edges }, ...future],
    });
  },

  redo: () => {
    const { future, nodes, edges, past } = get();
    if (future.length === 0) return;

    const next = future[0];
    set({
      nodes: next.nodes,
      edges: next.edges,
      past: [...past, { nodes, edges }],
      future: future.slice(1),
    });
  },

  setSaveStatus: (status) => set({
    saveStatus: status,
    lastSaved: status === 'saved' ? new Date() : get().lastSaved,
  }),

  toggleMinimap: () => set({ showMinimap: !get().showMinimap }),
  toggleVariables: () => set({ showVariables: !get().showVariables }),
}));
