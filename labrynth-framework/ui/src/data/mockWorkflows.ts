export interface MockWorkflow {
  id: string;
  name: string;
  description: string;
  icon: string;
  status: 'running' | 'success' | 'draft' | 'failed' | 'stopped';
  lastRun: string | null;
  runCount: number;
  successRate: number;
  tags: string[];
  nodeCount: number;
  createdAt: string;
  updatedAt: string;
}

export const mockWorkflows: MockWorkflow[] = [
  {
    id: 'wf-1',
    name: 'Customer Support Pipeline',
    description: 'Routes customer inquiries to appropriate support agents based on intent',
    icon: '🔄',
    status: 'running',
    lastRun: '2 min ago',
    runCount: 847,
    successRate: 94,
    tags: ['support', 'nlp', 'production'],
    nodeCount: 6,
    createdAt: '2024-12-01',
    updatedAt: '2024-12-13',
  },
  {
    id: 'wf-2',
    name: 'Data ETL Pipeline',
    description: 'Extracts, transforms, and loads data from multiple sources',
    icon: '📊',
    status: 'success',
    lastRun: '1 hour ago',
    runCount: 156,
    successRate: 98,
    tags: ['etl', 'data'],
    nodeCount: 8,
    createdAt: '2024-11-15',
    updatedAt: '2024-12-13',
  },
  {
    id: 'wf-3',
    name: 'ML Training Pipeline',
    description: 'Automated model training and evaluation workflow',
    icon: '🧠',
    status: 'draft',
    lastRun: null,
    runCount: 0,
    successRate: 0,
    tags: ['ml', 'training'],
    nodeCount: 4,
    createdAt: '2024-12-10',
    updatedAt: '2024-12-12',
  },
  {
    id: 'wf-4',
    name: 'Report Generator',
    description: 'Generates daily reports from analytics data',
    icon: '📝',
    status: 'failed',
    lastRun: '3 hours ago',
    runCount: 89,
    successRate: 87,
    tags: ['reporting'],
    nodeCount: 5,
    createdAt: '2024-11-20',
    updatedAt: '2024-12-13',
  },
  {
    id: 'wf-5',
    name: 'Slack Bot Workflow',
    description: 'Automated Slack bot for team notifications and updates',
    icon: '💬',
    status: 'running',
    lastRun: '15 min ago',
    runCount: 523,
    successRate: 96,
    tags: ['slack', 'notifications'],
    nodeCount: 7,
    createdAt: '2024-11-01',
    updatedAt: '2024-12-13',
  },
  {
    id: 'wf-6',
    name: 'Email Processor',
    description: 'Processes incoming emails and routes them to appropriate teams',
    icon: '📧',
    status: 'success',
    lastRun: '30 min ago',
    runCount: 1234,
    successRate: 92,
    tags: ['email', 'automation'],
    nodeCount: 9,
    createdAt: '2024-10-15',
    updatedAt: '2024-12-13',
  },
];

export interface AgentParameter {
  type: string;
  required: boolean;
  default?: any;
  description?: string;
}

export interface AgentOutput {
  type: string;
  description?: string;
}

export interface MockAgent {
  id: string;
  name: string;
  description: string;
  tags: string[];
  icon: string;
  parameters: Record<string, AgentParameter>;
  outputs: Record<string, AgentOutput>;
}

export const mockAgents: MockAgent[] = [
  {
    id: 'agent-1',
    name: 'Intent Classifier',
    description: 'Classifies user intent from text input using NLP',
    tags: ['nlp', 'classification'],
    icon: '🎯',
    parameters: {
      text: { type: 'string', required: true, description: 'Input text to classify' },
      context: { type: 'string', required: false, description: 'Additional context' }
    },
    outputs: {
      intent: { type: 'string', description: 'Classified intent' },
      confidence: { type: 'float', description: 'Confidence score 0-1' }
    }
  },
  {
    id: 'agent-2',
    name: 'Billing Support',
    description: 'Handles billing-related customer queries and issues',
    tags: ['support', 'billing'],
    icon: '💳',
    parameters: {
      query: { type: 'string', required: true, description: 'Customer query' },
      customer_id: { type: 'string', required: true, description: 'Customer ID' }
    },
    outputs: {
      response: { type: 'string', description: 'Support response' },
      action_taken: { type: 'string', description: 'Action performed' }
    }
  },
  {
    id: 'agent-3',
    name: 'Tech Support',
    description: 'Resolves technical issues and provides troubleshooting steps',
    tags: ['support', 'technical'],
    icon: '🔧',
    parameters: {
      issue: { type: 'string', required: true, description: 'Issue description' },
      product: { type: 'string', required: false, description: 'Product name' }
    },
    outputs: {
      solution: { type: 'string', description: 'Proposed solution' },
      escalate: { type: 'boolean', description: 'Should escalate?' }
    }
  },
  {
    id: 'agent-4',
    name: 'Response Formatter',
    description: 'Formats agent responses for customer delivery',
    tags: ['utility', 'formatting'],
    icon: '✍️',
    parameters: {
      content: { type: 'string', required: true, description: 'Content to format' },
      format: { type: 'string', required: false, default: 'friendly', description: 'Format style' }
    },
    outputs: {
      formatted_response: { type: 'string', description: 'Formatted response' }
    }
  },
];

export const logicNodes = [
  { id: 'if-else', name: 'If/Else', icon: '◇', description: 'Conditional branching' },
  { id: 'parallel', name: 'Parallel', icon: '⫘', description: 'Run in parallel' },
  { id: 'merge', name: 'Merge', icon: '⫗', description: 'Merge branches' },
];

export const utilityNodes = [
  { id: 'code', name: 'Code', icon: '📝', description: 'Execute code' },
  { id: 'http', name: 'HTTP', icon: '🌐', description: 'HTTP request' },
  { id: 'delay', name: 'Delay', icon: '⏱️', description: 'Time delay' },
];

export const ioNodes = [
  { id: 'input', name: 'Input', icon: '▶', description: 'Workflow input' },
  { id: 'output', name: 'Output', icon: '⏹', description: 'Workflow output' },
];
