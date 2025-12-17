import React, { useCallback, useRef, DragEvent } from "react";
import ReactFlow, {
  Background,
  Controls,
  addEdge,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  Connection,
  Handle,
  Position,
  NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import {
  ChevronDown,
  Play,
  Grid3x3,
  Zap,
  Share2,
  Plus,
  Search,
  Settings,
  ChevronRight,
  Cloud,
  HardDrive,
  AtSign,
  Copy,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  Edit2,
  Trash2,
  Sun,
  Moon,
  Clock,
  Webhook,
  Bot,
  Code,
  GitBranch,
  Shield,
  Users,
  BookOpen,
  Repeat,
  Database,
  FileText,
  Layers,
  MessageSquare,
  Variable,
  Workflow,
  Calendar,
  Mail,
  Github,
  Table,
  Home,
  Target,
  Link,
  Box,
  Wrench,
  ChevronUp,
  Copy as CopyIcon,
  Circle,
  RotateCcw,
  ArrowUpDown,
  ArrowDownUp,
  FolderArchive,
  FileBarChart,
  LifeBuoy,
  HelpCircle,
  ArrowLeft,
} from "lucide-react";
import { ConditionEditor } from "./ConditionEditor";
import { CustomEdge } from "./CustomEdge";
import { NodeActionButtons } from "./NodeActionButtons";
import { RunModal } from "./RunModal";
import { useTheme } from "../../App";

// Agent interface
interface Agent {
  id: string;
  project_id: string;
  name: string;
  description: string;
  entrypoint: string;
  tags: string[];
  parameters: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface AgentsResponse {
  agents: Agent[];
  count: number;
}

interface WorkflowBuilderV2Props {
  onBack?: () => void;
}

// Fetch agents from API
const fetchAgents = async (): Promise<AgentsResponse> => {
  const response = await fetch("http://127.0.0.1:8000/api/agents");
  if (!response.ok) {
    throw new Error(`Failed to fetch agents: ${response.statusText}`);
  }
  return response.json();
};

const initialNodes: Node[] = [];

const initialEdges: Edge[] = [];

// Toolbar data
const triggers = [
  { icon: "Play", color: "bg-blue-500", label: "Start", type: "trigger" },
  { icon: "Clock", color: "bg-blue-500", label: "Schedule", type: "trigger" },
  { icon: "Webhook", color: "bg-blue-500", label: "Webhook", type: "trigger" },
  { icon: "Table", color: "bg-pink-500", label: "Airtable", type: "trigger" },
  { icon: "Calendar", color: "bg-blue-500", label: "Calendly", type: "trigger" },
  { icon: "Github", color: "bg-gray-600", label: "GitHub", type: "trigger" },
  { icon: "Mail", color: "bg-gray-600", label: "Gmail", type: "trigger" },
  { icon: "FileText", color: "bg-gray-600", label: "Google Forms", type: "trigger" },
  { icon: "Target", color: "bg-orange-500", label: "HubSpot", type: "trigger" },
];

const blocks = [
  { icon: "Bot", color: "bg-purple-500", label: "Agent", type: "block" },
  { icon: "Code", color: "bg-blue-500", label: "API", type: "block" },
  { icon: "GitBranch", color: "bg-orange-500", label: "Condition", type: "block" },
  { icon: "Wrench", color: "bg-orange-500", label: "Function", type: "block" },
  { icon: "Shield", color: "bg-green-500", label: "Guardrails", type: "block" },
  { icon: "Users", color: "bg-emerald-500", label: "Human in the Loop", type: "block" },
  { icon: "BookOpen", color: "bg-cyan-500", label: "Knowledge", type: "block" },
  { icon: "Repeat", color: "bg-blue-500", label: "Loop", type: "block" },
  { icon: "Database", color: "bg-pink-500", label: "Memory", type: "block" },
  { icon: "FileText", color: "bg-amber-500", label: "Note", type: "block" },
  { icon: "Layers", color: "bg-blue-500", label: "Parallel", type: "block" },
  { icon: "MessageSquare", color: "bg-blue-500", label: "Response", type: "block" },
  { icon: "GitBranch", color: "bg-green-500", label: "Router", type: "block" },
  { icon: "Variable", color: "bg-purple-500", label: "Variables", type: "block" },
  { icon: "Clock", color: "bg-orange-500", label: "Wait", type: "block" },
  { icon: "Workflow", color: "bg-blue-500", label: "Workflow", type: "block" },
  { icon: "Link", color: "bg-amber-600", label: "Ahrefs", type: "block" },
  { icon: "Table", color: "bg-pink-500", label: "Airtable", type: "block" },
  { icon: "Database", color: "bg-blue-500", label: "Amazon DynamoDB", type: "block" },
  { icon: "Database", color: "bg-blue-500", label: "Amazon RDS", type: "block" },
  { icon: "Box", color: "bg-blue-500", label: "Amazon SQS", type: "block" },
  { icon: "Bot", color: "bg-gray-600", label: "Apify", type: "block" },
  { icon: "Target", color: "bg-lime-500", label: "Apollo", type: "block" },
  { icon: "FileText", color: "bg-gray-600", label: "Arxiv", type: "block" },
  { icon: "Home", color: "bg-pink-500", label: "Asana", type: "block" },
  { icon: "Bot", color: "bg-gray-600", label: "Browser Use", type: "block" },
];

// Get icon component by name
const getIconComponent = (iconName: string) => {
  const icons: Record<string, any> = {
    Play, Clock, Webhook, Bot, Code, GitBranch, Shield, Users, BookOpen,
    Repeat, Database, FileText, Layers, MessageSquare, Variable, Workflow,
    Calendar, Mail, Github, Table, Home, Target, Link, Box, Wrench,
    ChevronUp, CopyIcon, Circle, RotateCcw, ArrowUpDown, ArrowDownUp,
    FolderArchive, FileBarChart, LifeBuoy, HelpCircle,
  };
  return icons[iconName] || Box;
};

// Get icon color for node type
const getIconColor = (type: string): string => {
  if (type === "Agent") return "bg-purple-500";
  if (type === "Condition") return "bg-orange-500";
  if (type === "API") return "bg-blue-500";
  if (type === "Function") return "bg-orange-500";
  return "bg-purple-500";
};

// Custom Node Component
function CustomNode({ data, selected, id }: NodeProps) {
  const isDark = data.isDark !== undefined ? data.isDark : true;
  const fields = data.fields || [];
  const IconComponent = getIconComponent(data.icon || "Box");
  const iconColor = data.color || getIconColor(data.label);
  const portOrientation = data.portOrientation || "horizontal";
  const isRunning = data.isRunning || false;

  const inputPosition = portOrientation === "vertical" ? Position.Top : Position.Left;
  const outputPosition = portOrientation === "vertical" ? Position.Bottom : Position.Right;

  return (
    <div
      className={`min-w-[280px] rounded-lg ${
        isRunning
          ? "ring-2 ring-blue-500 ring-offset-2 animate-pulse"
          : selected
            ? "ring-2 ring-blue-500"
            : ""
      } ${isDark ? "bg-[#1a1a1a] border-gray-700" : "bg-white border-gray-300"} ${
        isRunning ? "border-2 border-dashed border-blue-500" : "border-2"
      }`}
    >
      <Handle type="target" position={inputPosition} className="!w-3 !h-3 !bg-gray-400" />

      {/* Header */}
      <div className={`flex items-center gap-2 px-3 py-2 ${isDark ? "border-gray-700" : "border-gray-300"} border-b`}>
        <div className={`w-5 h-5 flex items-center justify-center rounded ${iconColor}`}>
          <IconComponent className="w-3 h-3 text-white" />
        </div>
        <span className={`text-sm font-medium ${isDark ? "text-gray-200" : "text-gray-900"}`}>
          {data.label}
        </span>
      </div>

      {/* Fields */}
      <div className="px-3 py-2">
        {fields.length > 0 ? (
          fields.map((field: any, index: number) => (
            <div
              key={index}
              className={`flex items-center justify-between py-1.5 text-xs ${isDark ? "text-gray-400" : "text-gray-600"}`}
            >
              <span>{field.name}</span>
              <span className={`${isDark ? "text-gray-500" : "text-gray-400"}`}>{field.value}</span>
              {field.hasHandle && (
                <Handle
                  type="source"
                  position={outputPosition}
                  id={field.name.toLowerCase()}
                  className="!w-2 !h-2 !bg-red-500 !right-0"
                  style={{ top: `${((index + 1) * 100) / (fields.length + 1)}%` }}
                />
              )}
            </div>
          ))
        ) : (
          <div className={`text-xs ${isDark ? "text-gray-500" : "text-gray-400"} py-2`}>
            No configuration
          </div>
        )}
      </div>

      <Handle type="source" position={outputPosition} className="!w-3 !h-3 !bg-gray-400" />
    </div>
  );
}

const nodeTypes = { custom: CustomNode };
const edgeTypes = { custom: CustomEdge };

// Get default fields for different node types
const getDefaultFields = (type: string) => {
  if (type === "Agent") {
    return [
      { name: "Messages", value: "-" },
      { name: "Model", value: "claude-sonnet-4-5" },
      { name: "Tools", value: "-" },
      { name: "Memory", value: "None" },
      { name: "Temperature", value: "0.3" },
      { name: "Response Format", value: "-" },
      { name: "Error", value: "", hasHandle: true },
    ];
  }
  if (type === "Condition") {
    return [
      { name: "If", value: "-" },
      { name: "Else", value: "-" },
      { name: "Error", value: "", hasHandle: true },
    ];
  }
  if (type === "API") {
    return [
      { name: "URL", value: "-" },
      { name: "Method", value: "GET" },
      { name: "Headers", value: "-" },
      { name: "Body", value: "-" },
    ];
  }
  return [];
};

// ToolbarItem component with drag support
function ToolbarItem({
  icon,
  label,
  type,
  color,
  isDark,
}: {
  icon: string;
  label: string;
  type: string;
  color?: string;
  isDark: boolean;
}) {
  const onDragStart = (event: DragEvent) => {
    event.dataTransfer.setData("application/reactflow", JSON.stringify({ label, icon, color, type }));
    event.dataTransfer.effectAllowed = "move";
  };

  const IconComponent = getIconComponent(icon);

  return (
    <div
      className={`flex items-center gap-2 p-2 ${isDark ? "hover:bg-[#1a1a1a]" : "hover:bg-gray-100"} rounded cursor-grab active:cursor-grabbing transition-colors`}
      draggable
      onDragStart={onDragStart}
    >
      <div className={`w-5 h-5 flex items-center justify-center rounded ${color || "bg-gray-400"}`}>
        <IconComponent className="w-3 h-3 text-white" />
      </div>
      <span className={`text-sm ${isDark ? "text-gray-300" : "text-gray-700"}`}>{label}</span>
    </div>
  );
}

export function WorkflowBuilderV2({ onBack }: WorkflowBuilderV2Props) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [activeTab, setActiveTab] = React.useState<"copilot" | "toolbar" | "editor">("copilot");
  const [selectedNode, setSelectedNode] = React.useState<Node | null>(null);
  const [toolbarSearch, setToolbarSearch] = React.useState("");
  const [agents, setAgents] = React.useState<Agent[]>([]);
  const [isLoadingAgents, setIsLoadingAgents] = React.useState(false);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<any>(null);
  let nodeIdCounter = useRef(1);

  // State for left sidebar
  const [runsSearch, setRunsSearch] = React.useState("");
  const [selectedRun, setSelectedRun] = React.useState<any>(null);
  const [isRunModalOpen, setIsRunModalOpen] = React.useState(false);

  // State for running simulation
  const [isRunning, setIsRunning] = React.useState(false);

  // Current workflow data
  const currentWorkflow = {
    id: "workflow-001",
    name: "Lead Generation Pipeline",
    description: "Automated lead generation and qualification workflow",
    createdAt: "2024-01-15T10:30:00Z",
    updatedAt: "2024-01-18T14:22:00Z",
    status: "active" as const,
  };

  // Mock runs data
  const runs = [
    {
      id: "RUN-2024-001",
      status: "success" as const,
      startTime: "2024-01-18T14:22:00Z",
      endTime: "2024-01-18T14:24:30Z",
      duration: 150000,
      triggeredBy: "Manual",
      steps: [
        { id: "step-1", name: "Start Trigger", status: "success" as const, duration: 1200, startTime: "2024-01-18T14:22:00Z", endTime: "2024-01-18T14:22:01Z" },
        { id: "step-2", name: "Research Agent", status: "success" as const, duration: 45000, startTime: "2024-01-18T14:22:01Z", endTime: "2024-01-18T14:22:46Z" },
      ],
      comments: [{ id: "comment-1", author: "John Doe", text: "This run completed successfully!", timestamp: "2024-01-18T15:00:00Z" }],
    },
  ];

  // Fetch agents on mount
  React.useEffect(() => {
    const loadAgents = async () => {
      setIsLoadingAgents(true);
      try {
        const response = await fetchAgents();
        setAgents(response.agents);
      } catch (error) {
        console.error("Failed to fetch agents:", error);
      } finally {
        setIsLoadingAgents(false);
      }
    };
    loadAgents();
  }, []);

  // Handle edge deletion
  const handleDeleteEdge = useCallback((edgeId: string) => {
    setEdges((eds) => eds.filter((edge) => edge.id !== edgeId));
  }, [setEdges]);

  const onConnect = useCallback((params: Connection) => {
    const newEdge = { ...params, type: "custom", data: { onDelete: handleDeleteEdge } };
    setEdges((eds) => addEdge(newEdge, eds));
  }, [setEdges, handleDeleteEdge]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
    setActiveTab("editor");
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleDeleteNode = useCallback((nodeId: string) => {
    setNodes((nds) => nds.filter((node) => node.id !== nodeId));
    setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    setSelectedNode(null);
  }, [setNodes, setEdges]);

  const handleTogglePortOrientation = useCallback((nodeId: string) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, portOrientation: node.data.portOrientation === "vertical" ? "horizontal" : "vertical" } }
          : node
      )
    );

    setTimeout(() => {
      const connectedEdges = edges.filter((e) => e.source === nodeId || e.target === nodeId);
      const unconnectedEdges = edges.filter((e) => e.source !== nodeId && e.target !== nodeId);
      setEdges(unconnectedEdges);
      setTimeout(() => {
        const newEdges = connectedEdges.map((edge) => ({ ...edge, id: `${edge.id}-${Date.now()}-${Math.random()}` }));
        setEdges((eds) => [...eds, ...newEdges]);
      }, 100);
    }, 0);
  }, [setNodes, setEdges, edges]);

  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback((event: DragEvent) => {
    event.preventDefault();
    if (!reactFlowInstance) return;

    const data = event.dataTransfer.getData("application/reactflow");
    if (!data) return;

    const { label, icon, color, type } = JSON.parse(data);
    const position = reactFlowInstance.screenToFlowPosition({ x: event.clientX, y: event.clientY });

    const newNode: Node = {
      id: `node-${nodeIdCounter.current++}`,
      type: "custom",
      position,
      data: { label, icon, color, type, isDark, fields: getDefaultFields(label) },
    };

    setNodes((nds) => nds.concat(newNode));
  }, [reactFlowInstance, setNodes, isDark]);

  // Filter blocks based on search
  const filteredTriggers = triggers.filter((item) => item.label.toLowerCase().includes(toolbarSearch.toLowerCase()));
  const filteredBlocks = blocks.filter((item) => item.label.toLowerCase().includes(toolbarSearch.toLowerCase()));
  const filteredAgents = agents.filter(
    (agent) =>
      agent.name.toLowerCase().includes(toolbarSearch.toLowerCase()) ||
      agent.description.toLowerCase().includes(toolbarSearch.toLowerCase()) ||
      agent.tags.some((tag) => tag.toLowerCase().includes(toolbarSearch.toLowerCase()))
  );

  // Update existing nodes when theme changes
  React.useEffect(() => {
    setNodes((nds) => nds.map((node) => ({ ...node, data: { ...node.data, isDark } })));
  }, [isDark, setNodes]);

  // Handle Run button
  const handleRun = useCallback(async () => {
    if (nodes.length === 0 || isRunning) return;
    setIsRunning(true);

    for (let i = 0; i < nodes.length; i++) {
      const nodeId = nodes[i].id;
      setNodes((nds) => nds.map((node) => ({ ...node, data: { ...node.data, isRunning: node.id === nodeId } })));
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }

    setNodes((nds) => nds.map((node) => ({ ...node, data: { ...node.data, isRunning: false } })));
    setIsRunning(false);
  }, [nodes, isRunning, setNodes]);

  // Handle Share button
  const handleShare = useCallback(() => {
    const graphData = {
      nodes: nodes.map((node) => ({
        id: node.id, type: node.type, position: node.position,
        data: { label: node.data.label, icon: node.data.icon, color: node.data.color, type: node.data.type, fields: node.data.fields, portOrientation: node.data.portOrientation },
      })),
      edges: edges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target, sourceHandle: edge.sourceHandle, targetHandle: edge.targetHandle, type: edge.type })),
    };
    console.log("Graph JSON:", JSON.stringify(graphData, null, 2));
  }, [nodes, edges]);

  // Handle Auto Layout
  const handleAutoLayout = useCallback(() => {
    if (nodes.length === 0) return;

    const adjacencyMap = new Map<string, string[]>();
    const inDegree = new Map<string, number>();

    nodes.forEach((node) => {
      adjacencyMap.set(node.id, []);
      inDegree.set(node.id, 0);
    });

    edges.forEach((edge) => {
      const children = adjacencyMap.get(edge.source) || [];
      children.push(edge.target);
      adjacencyMap.set(edge.source, children);
      inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
    });

    const startNodes = nodes.filter((node) => inDegree.get(node.id) === 0);
    const rootNodes = startNodes.length > 0 ? startNodes : [nodes[0]];

    const levels = new Map<string, number>();
    const visited = new Set<string>();
    const queue: Array<{ id: string; level: number }> = [];

    rootNodes.forEach((node) => {
      queue.push({ id: node.id, level: 0 });
      visited.add(node.id);
    });

    while (queue.length > 0) {
      const { id, level } = queue.shift()!;
      levels.set(id, level);
      const children = adjacencyMap.get(id) || [];
      children.forEach((childId) => {
        if (!visited.has(childId)) {
          visited.add(childId);
          queue.push({ id: childId, level: level + 1 });
        }
      });
    }

    nodes.forEach((node) => {
      if (!levels.has(node.id)) levels.set(node.id, 0);
    });

    const nodesByLevel = new Map<number, Node[]>();
    nodes.forEach((node) => {
      const level = levels.get(node.id) || 0;
      if (!nodesByLevel.has(level)) nodesByLevel.set(level, []);
      nodesByLevel.get(level)!.push(node);
    });

    const horizontalSpacing = 400;
    const verticalSpacing = 120;
    const startX = 100;
    const startY = 100;

    const updatedNodes = nodes.map((node) => {
      const level = levels.get(node.id) || 0;
      const nodesInLevel = nodesByLevel.get(level) || [];
      const indexInLevel = nodesInLevel.findIndex((n) => n.id === node.id);
      const levelHeight = (nodesInLevel.length - 1) * verticalSpacing;
      const offsetY = -levelHeight / 2;

      return { ...node, position: { x: startX + level * horizontalSpacing, y: startY + offsetY + indexInLevel * verticalSpacing } };
    });

    setNodes(updatedNodes);

    setTimeout(() => {
      if (reactFlowInstance) reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
    }, 50);
  }, [nodes, edges, setNodes, reactFlowInstance]);

  return (
    <div className={`h-screen w-screen flex flex-col ${isDark ? "bg-[#0a0a0a] text-gray-200" : "bg-gray-50 text-gray-900"}`}>
      {/* Top Bar */}
      <div className={`h-14 ${isDark ? "bg-[#1a1a1a] border-gray-800" : "bg-white border-gray-200"} border-b flex items-center justify-between px-4`}>
        <div className="flex items-center gap-3">
          {onBack && (
            <button
              onClick={onBack}
              className={`flex items-center gap-2 px-3 py-1.5 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-100"} rounded text-sm`}
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>
          )}
          <div className={`flex items-center gap-2 text-sm ${isDark ? "text-gray-400" : "text-gray-600"}`}>
            <span>Anonymous...</span>
            <ChevronDown className="w-4 h-4" />
          </div>
          <button
            onClick={handleRun}
            disabled={isRunning || nodes.length === 0}
            className={`flex items-center gap-2 px-3 py-1.5 ${
              isRunning || nodes.length === 0
                ? isDark ? "bg-[#1a1a1a] border-gray-800 text-gray-600 cursor-not-allowed" : "bg-gray-50 border-gray-200 text-gray-400 cursor-not-allowed"
                : isDark ? "bg-[#2a2a2a] hover:bg-[#333333] border-gray-700" : "bg-gray-100 hover:bg-gray-200 border-gray-300"
            } rounded text-sm border`}
          >
            <Play className="w-3.5 h-3.5" />
            <span>{isRunning ? "Running..." : "Run"}</span>
            <ChevronDown className="w-3 h-3" />
          </button>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleAutoLayout} disabled={nodes.length === 0}
            className={`flex items-center gap-2 px-3 py-1.5 ${
              nodes.length === 0
                ? isDark ? "bg-[#1a1a1a] border-gray-800 text-gray-600 cursor-not-allowed" : "bg-gray-50 border-gray-200 text-gray-400 cursor-not-allowed"
                : isDark ? "bg-[#2a2a2a] hover:bg-[#333333] border-gray-700" : "bg-gray-100 hover:bg-gray-200 border-gray-300"
            } rounded text-sm border`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Auto Layout</span>
          </button>
          <button onClick={handleShare} className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-sm text-white">
            <Share2 className="w-3.5 h-3.5" />
            <span>Share</span>
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <div className={`w-64 ${isDark ? "bg-[#0a0a0a] border-gray-800" : "bg-white border-gray-200"} border-r flex flex-col`}>
          {/* Workflow Details */}
          <div className={`p-4 ${isDark ? "border-gray-800" : "border-gray-200"} border-b`}>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-green-500"></div>
              <h2 className={`text-sm font-semibold ${isDark ? "text-gray-200" : "text-gray-900"}`}>{currentWorkflow.name}</h2>
            </div>
            <p className={`text-xs ${isDark ? "text-gray-400" : "text-gray-600"} mb-3`}>{currentWorkflow.description}</p>
            <div className="flex items-center gap-4 text-xs">
              <div><span className={`${isDark ? "text-gray-500" : "text-gray-400"}`}>Status: </span><span className="text-green-500">Active</span></div>
              <div><span className={`${isDark ? "text-gray-500" : "text-gray-400"}`}>{nodes.length} nodes</span></div>
            </div>
          </div>

          {/* Search Runs */}
          <div className={`p-3 ${isDark ? "border-gray-800" : "border-gray-200"} border-b`}>
            <div className={`flex items-center gap-2 ${isDark ? "bg-[#1a1a1a]" : "bg-gray-100"} rounded px-3 py-1.5`}>
              <Search className={`w-4 h-4 ${isDark ? "text-gray-500" : "text-gray-400"}`} />
              <input
                type="text"
                placeholder="Search runs..."
                value={runsSearch}
                onChange={(e) => setRunsSearch(e.target.value)}
                className={`flex-1 bg-transparent border-none outline-none text-sm ${isDark ? "text-gray-300 placeholder-gray-500" : "text-gray-900 placeholder-gray-400"}`}
              />
            </div>
          </div>

          {/* Runs List */}
          <div className="flex-1 overflow-auto">
            <div className="p-3">
              <div className="flex items-center justify-between mb-3">
                <h3 className={`text-xs font-medium ${isDark ? "text-gray-400" : "text-gray-500"} uppercase`}>Recent Runs ({runs.length})</h3>
              </div>
              <div className="space-y-2">
                {runs
                  .filter((run) => run.id.toLowerCase().includes(runsSearch.toLowerCase()) || run.triggeredBy.toLowerCase().includes(runsSearch.toLowerCase()))
                  .map((run) => {
                    const statusColors = { success: "bg-green-500", error: "bg-red-500", running: "bg-blue-500", pending: "bg-gray-400" };
                    const formatDate = (isoString: string) => {
                      const date = new Date(isoString);
                      return date.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
                    };

                    return (
                      <button
                        key={run.id}
                        onClick={() => { setSelectedRun(run); setIsRunModalOpen(true); }}
                        className={`w-full ${isDark ? "bg-[#1a1a1a] hover:bg-[#2a2a2a]" : "bg-gray-50 hover:bg-gray-100"} rounded-lg p-3 text-left transition-colors`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className={`text-xs font-medium ${isDark ? "text-gray-300" : "text-gray-700"}`}>{run.id}</span>
                          <div className={`w-2 h-2 rounded-full ${statusColors[run.status]}`}></div>
                        </div>
                        <div className={`text-xs ${isDark ? "text-gray-500" : "text-gray-400"} mb-1`}>{formatDate(run.startTime)}</div>
                        <div className="flex items-center justify-between text-xs">
                          <span className={`${isDark ? "text-gray-500" : "text-gray-400"}`}>{run.triggeredBy}</span>
                          {run.status === "success" && <span className={`${isDark ? "text-gray-500" : "text-gray-400"}`}>{Math.floor(run.duration / 1000)}s</span>}
                        </div>
                      </button>
                    );
                  })}
              </div>
            </div>
          </div>

          <div className="flex-1"></div>

          {/* Bottom Menu */}
          <div className={`${isDark ? "border-gray-800" : "border-gray-200"} border-t`}>
            <div className="p-3">
              <div className="flex items-center justify-between mb-2">
                <span className={`text-xs ${isDark ? "text-gray-400" : "text-gray-600"}`}>Free</span>
                <span className={`text-xs ${isDark ? "text-gray-400" : "text-gray-600"}`}>$0.52 / $10.00</span>
                <button className="text-xs text-pink-500 hover:text-pink-400">Upgrade</button>
              </div>
              <div className={`h-1.5 ${isDark ? "bg-[#1a1a1a]" : "bg-gray-200"} rounded-full overflow-hidden flex`}>
                <div className="w-[5%] h-full bg-blue-500"></div>
              </div>
            </div>
            <div className={`${isDark ? "border-gray-800" : "border-gray-200"} border-t`}>
              {[{ icon: FileBarChart, label: "Logs" }, { icon: Layers, label: "Templates" }, { icon: BookOpen, label: "Knowledge Base" }, { icon: HelpCircle, label: "Help" }, { icon: Settings, label: "Settings" }].map((item) => (
                <button
                  key={item.label}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm ${isDark ? "text-gray-400 hover:bg-[#1a1a1a] hover:text-gray-200" : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"} transition-colors`}
                >
                  <item.icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Main Canvas */}
        <div className="flex-1 relative" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            connectionLineType="smoothstep"
            defaultEdgeOptions={{ type: "smoothstep" }}
            fitView
            className={isDark ? "bg-[#0a0a0a]" : "bg-gray-100"}
          >
            <Background color={isDark ? "#1a1a1a" : "#d1d5db"} gap={16} />
            <Controls className={isDark ? "!bg-[#1a1a1a] !border-gray-700" : "!bg-white !border-gray-300"} />
          </ReactFlow>

          {selectedNode && reactFlowInstance && (() => {
            const currentNode = nodes.find((n) => n.id === selectedNode.id);
            if (!currentNode) return null;

            return (
              <NodeActionButtons
                nodeId={currentNode.id}
                nodePosition={currentNode.position}
                portOrientation={currentNode.data.portOrientation || "horizontal"}
                onDelete={handleDeleteNode}
                onTogglePortOrientation={handleTogglePortOrientation}
                isDark={isDark}
                viewport={reactFlowInstance.getViewport()}
              />
            );
          })()}

          {nodes.length === 0 && (
            <div className={`absolute bottom-4 left-1/2 transform -translate-x-1/2 text-xs ${isDark ? "text-gray-500" : "text-gray-400"}`}>
              No trigger set
            </div>
          )}
        </div>

        {/* Right Sidebar */}
        <div className={`w-80 ${isDark ? "bg-[#0a0a0a] border-gray-800" : "bg-white border-gray-200"} border-l flex flex-col`}>
          <div className={`flex ${isDark ? "border-gray-800" : "border-gray-200"} border-b`}>
            {(["copilot", "toolbar", "editor"] as const).map((tab) => (
              <button
                key={tab}
                className={`flex-1 px-4 py-2 text-sm cursor-pointer ${
                  activeTab === tab
                    ? `border-b-2 border-blue-500 ${isDark ? "text-gray-200" : "text-gray-900"}`
                    : `${isDark ? "text-gray-400 hover:text-gray-200 hover:bg-[#1a1a1a]" : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"}`
                }`}
                onClick={() => setActiveTab(tab)}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {/* Copilot Tab */}
          {activeTab === "copilot" && (
            <>
              <div className={`p-4 ${isDark ? "border-gray-800" : "border-gray-200"} border-b flex items-center justify-between`}>
                <span className="text-sm font-medium">New Chat</span>
                <div className="flex items-center gap-2">
                  <button className={`p-1 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-100"} rounded`}><Plus className={`w-4 h-4 ${isDark ? "text-gray-400" : "text-gray-600"}`} /></button>
                  <button className={`p-1 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-100"} rounded`}><RefreshCw className={`w-4 h-4 ${isDark ? "text-gray-400" : "text-gray-600"}`} /></button>
                </div>
              </div>
              <div className="flex-1 overflow-auto p-4">
                <div className={`${isDark ? "bg-[#1a1a1a]" : "bg-gray-100"} rounded-lg p-4 mb-4`}>
                  <div className={`text-sm ${isDark ? "text-gray-300" : "text-gray-700"} leading-relaxed mb-3`}>
                    <span className="italic">Unauthorized request. You need a valid API key to use the copilot. You can get one by going to </span>
                    <a href="#" className="text-blue-500 hover:underline">strn.ai settings</a>
                    <span className="italic"> and generating one there.</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button className={`p-1.5 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-200"} rounded`}><Copy className={`w-4 h-4 ${isDark ? "text-gray-400" : "text-gray-600"}`} /></button>
                    <button className={`p-1.5 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-200"} rounded`}><ThumbsUp className={`w-4 h-4 ${isDark ? "text-gray-400" : "text-gray-600"}`} /></button>
                    <button className={`p-1.5 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-200"} rounded`}><ThumbsDown className={`w-4 h-4 ${isDark ? "text-gray-400" : "text-gray-600"}`} /></button>
                  </div>
                </div>
              </div>
              <div className={`${isDark ? "border-gray-800" : "border-gray-200"} border-t p-4`}>
                <div className={`${isDark ? "bg-[#1a1a1a]" : "bg-gray-100"} rounded-lg flex items-center px-3 py-2 mb-3`}>
                  <button className={`p-1 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-200"} rounded`}><AtSign className={`w-4 h-4 ${isDark ? "text-gray-400" : "text-gray-600"}`} /></button>
                  <input type="text" placeholder="Plan, search, build anything" className={`flex-1 bg-transparent border-none outline-none text-sm ${isDark ? "text-gray-300 placeholder-gray-500" : "text-gray-900 placeholder-gray-400"} px-2`} />
                </div>
                <div className="flex items-center gap-2">
                  <button className={`flex items-center gap-1.5 px-3 py-1.5 text-xs ${isDark ? "bg-[#1a1a1a] hover:bg-[#2a2a2a]" : "bg-gray-100 hover:bg-gray-200"} rounded`}>
                    <HardDrive className={`w-3.5 h-3.5 ${isDark ? "text-gray-400" : "text-gray-600"}`} />
                    <span className={isDark ? "text-gray-400" : "text-gray-600"}>Build</span>
                  </button>
                  <button className={`flex items-center gap-1.5 px-3 py-1.5 text-xs ${isDark ? "bg-[#1a1a1a] hover:bg-[#2a2a2a]" : "bg-gray-100 hover:bg-gray-200"} rounded`}>
                    <Cloud className={`w-3.5 h-3.5 ${isDark ? "text-gray-400" : "text-gray-600"}`} />
                    <span className={isDark ? "text-gray-400" : "text-gray-600"}>Cloud</span>
                  </button>
                  <button className={`p-1.5 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-200"} rounded ml-auto`}><ChevronRight className={`w-4 h-4 ${isDark ? "text-gray-400" : "text-gray-600"}`} /></button>
                </div>
              </div>
            </>
          )}

          {/* Toolbar Tab */}
          {activeTab === "toolbar" && (
            <>
              <div className={`p-4 ${isDark ? "border-gray-800" : "border-gray-200"} border-b`}>
                <div className={`${isDark ? "bg-[#1a1a1a]" : "bg-gray-100"} rounded-lg flex items-center px-3 py-2`}>
                  <Search className={`w-4 h-4 ${isDark ? "text-gray-400" : "text-gray-600"}`} />
                  <input
                    type="text"
                    placeholder="Search blocks..."
                    value={toolbarSearch}
                    onChange={(e) => setToolbarSearch(e.target.value)}
                    className={`flex-1 bg-transparent border-none outline-none text-sm ${isDark ? "text-gray-300 placeholder-gray-500" : "text-gray-900 placeholder-gray-400"} px-2`}
                  />
                </div>
              </div>
              <div className="flex-1 overflow-auto">
                {filteredTriggers.length > 0 && (
                  <div className="p-4">
                    <h3 className={`text-xs font-medium ${isDark ? "text-gray-400" : "text-gray-500"} mb-3`}>Triggers</h3>
                    <div className="space-y-1">
                      {filteredTriggers.map((trigger) => (
                        <ToolbarItem key={trigger.label} icon={trigger.icon} label={trigger.label} type={trigger.type} color={trigger.color} isDark={isDark} />
                      ))}
                    </div>
                  </div>
                )}
                {filteredBlocks.length > 0 && (
                  <div className="p-4">
                    <h3 className={`text-xs font-medium ${isDark ? "text-gray-400" : "text-gray-500"} mb-3`}>Blocks</h3>
                    <div className="space-y-1">
                      {filteredBlocks.map((block) => (
                        <ToolbarItem key={block.label} icon={block.icon} label={block.label} type={block.type} color={block.color} isDark={isDark} />
                      ))}
                    </div>
                  </div>
                )}
                {filteredAgents.length > 0 && (
                  <div className="p-4">
                    <h3 className={`text-xs font-medium ${isDark ? "text-gray-400" : "text-gray-500"} mb-3`}>Agents</h3>
                    <div className="space-y-1">
                      {filteredAgents.map((agent) => (
                        <ToolbarItem key={agent.id} icon="Bot" label={agent.name} type="agent" color="bg-purple-500" isDark={isDark} />
                      ))}
                    </div>
                  </div>
                )}
                {filteredTriggers.length === 0 && filteredBlocks.length === 0 && filteredAgents.length === 0 && toolbarSearch && (
                  <div className={`p-4 text-center text-sm ${isDark ? "text-gray-500" : "text-gray-400"}`}>No blocks found for "{toolbarSearch}"</div>
                )}
              </div>
            </>
          )}

          {/* Editor Tab */}
          {activeTab === "editor" && (
            <>
              <div className={`p-4 ${isDark ? "border-gray-800" : "border-gray-200"} border-b`}><span className="text-sm font-medium">Editor</span></div>
              {!selectedNode ? (
                <div className="flex-1 flex items-center justify-center p-4">
                  <p className={`text-sm ${isDark ? "text-gray-500" : "text-gray-400"}`}>Select a block to edit</p>
                </div>
              ) : (
                <div className="flex-1 overflow-auto">
                  <div className={`p-4 ${isDark ? "border-gray-800" : "border-gray-200"} border-b`}>
                    <div className="flex items-center gap-2 mb-4">
                      <div className={`w-5 h-5 flex items-center justify-center rounded ${selectedNode.data.color || getIconColor(selectedNode.data.label)}`}>
                        {(() => { const EditorIcon = getIconComponent(selectedNode.data.icon || "Box"); return <EditorIcon className="w-3 h-3 text-white" />; })()}
                      </div>
                      <span className="text-sm font-medium">{selectedNode.data.label}</span>
                      <button className={`ml-auto p-1 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-100"} rounded`}><Edit2 className={`w-3.5 h-3.5 ${isDark ? "text-gray-400" : "text-gray-600"}`} /></button>
                    </div>
                  </div>
                  {selectedNode.data.label === "Condition" ? (
                    <ConditionEditor isDark={isDark} nodeName={selectedNode.data.label} />
                  ) : (
                    <div className="p-4">
                      <div className="flex items-center justify-between mb-3"><h3 className={`text-xs font-medium ${isDark ? "text-gray-400" : "text-gray-500"}`}>Inputs</h3></div>
                      <div className="mb-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className={`text-sm ${isDark ? "text-gray-300" : "text-gray-700"}`}>Input 1</span>
                          <div className="flex items-center gap-1">
                            <button className={`p-1 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-100"} rounded`}><Plus className={`w-3 h-3 ${isDark ? "text-gray-400" : "text-gray-600"}`} /></button>
                            <button className={`p-1 ${isDark ? "hover:bg-[#2a2a2a]" : "hover:bg-gray-100"} rounded`}><Trash2 className={`w-3 h-3 ${isDark ? "text-gray-400" : "text-gray-600"}`} /></button>
                          </div>
                        </div>
                        <div className="mb-3">
                          <label className={`block text-xs ${isDark ? "text-gray-400" : "text-gray-500"} mb-1.5`}>Name</label>
                          <input type="text" defaultValue="firstName" className={`w-full ${isDark ? "bg-[#1a1a1a] border-gray-700 text-gray-300" : "bg-white border-gray-300 text-gray-900"} border rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500`} />
                        </div>
                        <div className="mb-3">
                          <label className={`block text-xs ${isDark ? "text-gray-400" : "text-gray-500"} mb-1.5`}>Type</label>
                          <select className={`w-full ${isDark ? "bg-[#1a1a1a] border-gray-700 text-gray-300" : "bg-white border-gray-300 text-gray-900"} border rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500`}>
                            <option>String</option>
                            <option>Number</option>
                            <option>Boolean</option>
                            <option>Object</option>
                            <option>Array</option>
                          </select>
                        </div>
                        <div className="mb-3">
                          <label className={`block text-xs ${isDark ? "text-gray-400" : "text-gray-500"} mb-1.5`}>Value</label>
                          <input type="text" placeholder="Enter test value" className={`w-full ${isDark ? "bg-[#1a1a1a] border-gray-700 text-gray-300 placeholder-gray-600" : "bg-white border-gray-300 text-gray-900 placeholder-gray-400"} border rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500`} />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Run Modal */}
      {isRunModalOpen && selectedRun && (
        <RunModal
          run={selectedRun}
          isDark={isDark}
          onClose={() => { setIsRunModalOpen(false); setSelectedRun(null); }}
        />
      )}
    </div>
  );
}
