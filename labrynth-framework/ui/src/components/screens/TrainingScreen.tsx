import { ChevronDown, Plus, Play } from 'lucide-react';
import { useState } from 'react';

const testCases = [
  {
    name: 'Test Case 1: Basic Analysis',
    input: 'Simple dataset with 5 values',
    expected: 'Trend detection',
    result: 'Match',
    status: 'passed',
  },
  {
    name: 'Test Case 2: Anomaly Detection',
    input: 'Dataset with outlier',
    expected: 'Identify outlier',
    result: 'Match',
    status: 'passed',
  },
  {
    name: 'Test Case 3: Edge Case - Empty Data',
    input: 'Empty array',
    expected: 'Error message',
    result: 'Crashed',
    status: 'failed',
  },
  {
    name: 'Test Case 4: Large Dataset',
    input: '10,000 records',
    expected: '',
    result: 'Not yet run',
    status: 'pending',
  },
];

export function TrainingScreen() {
  const [selectedAgent, setSelectedAgent] = useState('Agent A - Data Analyzer');

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-semibold text-[#F8FAFC] mb-1">Training</h1>
        <p className="text-sm text-[#94A3B8]">Train and fine-tune your AI agents</p>
      </div>

      {/* Agent Selector */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm text-[#94A3B8]">Select Agent:</span>
          <button className="flex items-center gap-2 px-4 py-2 bg-[#1E293B] border border-[rgba(148,163,184,0.2)] rounded-lg text-sm text-[#F8FAFC] hover:bg-[rgba(255,255,255,0.05)] transition-colors">
            {selectedAgent}
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>

        <button className="flex items-center gap-2 bg-[#8B5CF6] hover:bg-[#7C3AED] text-white px-4 py-2 rounded-lg transition-colors text-sm">
          <Plus className="w-4 h-4" />
          New Training Run
        </button>
      </div>

      {/* Training Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trainer Panel */}
        <div className="bg-[#1E293B] border border-[rgba(148,163,184,0.1)] rounded-xl overflow-hidden">
          <div className="p-5 border-b border-[rgba(148,163,184,0.1)]">
            <h3 className="text-base font-semibold text-[#F8FAFC]">TRAINER</h3>
          </div>
          
          <div className="p-5 space-y-4">
            {/* Training Mode */}
            <div className="flex items-center gap-3">
              <span className="text-sm text-[#94A3B8]">Training Mode:</span>
              <span className="flex items-center gap-2 px-3 py-1 bg-[rgba(16,185,129,0.1)] text-[#10B981] rounded-full text-sm">
                <span className="w-2 h-2 bg-[#10B981] rounded-full"></span>
                Active
              </span>
            </div>

            {/* Input */}
            <div>
              <label className="block text-sm font-medium text-[#F8FAFC] mb-2">INPUT</label>
              <textarea
                className="w-full bg-[#0F172A] border border-[rgba(148,163,184,0.2)] rounded-lg p-3 text-sm text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#8B5CF6] focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] font-mono"
                rows={8}
                defaultValue={`Analyze this dataset:

{
  "sales": [120, 145, 89, 234, 167],
  "region": "NA",
  "period": "Q4"
}`}
              />
            </div>

            {/* Expected Output */}
            <div>
              <label className="block text-sm font-medium text-[#F8FAFC] mb-2">EXPECTED OUTPUT</label>
              <textarea
                className="w-full bg-[#0F172A] border border-[rgba(148,163,184,0.2)] rounded-lg p-3 text-sm text-[#F8FAFC] placeholder:text-[#64748B] focus:border-[#8B5CF6] focus:outline-none focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] font-mono"
                rows={6}
                defaultValue={`{
  "trend": "increasing",
  "anomalies": [89],
  "avg": 151
}`}
              />
            </div>

            {/* Run Button */}
            <button className="w-full flex items-center justify-center gap-2 bg-[#8B5CF6] hover:bg-[#7C3AED] text-white px-4 py-2 rounded-lg transition-colors text-sm">
              <Play className="w-4 h-4" />
              Run Training
            </button>
          </div>
        </div>

        {/* Output Preview Panel */}
        <div className="bg-[#1E293B] border border-[rgba(148,163,184,0.1)] rounded-xl overflow-hidden">
          <div className="p-5 border-b border-[rgba(148,163,184,0.1)]">
            <h3 className="text-base font-semibold text-[#F8FAFC]">OUTPUT PREVIEW</h3>
          </div>
          
          <div className="p-5 flex items-center justify-center h-[calc(100%-60px)] text-sm text-[#64748B]">
            Agent will process input and generate output here...
          </div>
        </div>
      </div>

      {/* Test Cases Section */}
      <div className="bg-[#1E293B] border border-[rgba(148,163,184,0.1)] rounded-xl overflow-hidden">
        <div className="p-5 border-b border-[rgba(148,163,184,0.1)] flex items-center justify-between">
          <h3 className="text-base font-semibold text-[#F8FAFC]">TEST CASES</h3>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[#94A3B8] hover:text-[#F8FAFC] rounded-lg transition-colors text-sm">
            <Plus className="w-4 h-4" />
            Add
          </button>
        </div>

        <div className="divide-y divide-[rgba(148,163,184,0.1)]">
          {testCases.map((test, index) => (
            <TestCaseRow key={index} testCase={test} />
          ))}
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-[rgba(148,163,184,0.1)] flex items-center justify-between">
          <span className="text-sm text-[#94A3B8]">
            Test Results: <span className="text-[#10B981]">2/4 Passed (50%)</span>
          </span>
          <button className="px-4 py-2 bg-[#8B5CF6] hover:bg-[#7C3AED] text-white rounded-lg transition-colors text-sm">
            Run All Tests
          </button>
        </div>
      </div>
    </div>
  );
}

function TestCaseRow({ testCase }: { testCase: any }) {
  const statusConfig = {
    passed: { icon: '✅', color: '#10B981', label: 'PASSED' },
    failed: { icon: '❌', color: '#EF4444', label: 'FAILED' },
    pending: { icon: '⏳', color: '#64748B', label: 'PENDING' },
    running: { icon: '🔄', color: '#3B82F6', label: 'RUNNING' },
  };

  const status = statusConfig[testCase.status as keyof typeof statusConfig];

  return (
    <div className="p-4 hover:bg-[rgba(255,255,255,0.02)] transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-start gap-3 flex-1">
          <span className="text-xl">{status.icon}</span>
          <div>
            <h4 className="text-sm font-medium text-[#F8FAFC] mb-1">{testCase.name}</h4>
            <div className="space-y-0.5 text-xs text-[#94A3B8]">
              <p>Input: {testCase.input}</p>
              {testCase.expected && <p>Expected: {testCase.expected} • Result: {testCase.result}</p>}
              {testCase.status === 'pending' && <p>Status: {testCase.result}</p>}
            </div>
          </div>
        </div>
        <span className="text-xs font-medium" style={{ color: status.color }}>
          {status.label}
        </span>
      </div>

      {testCase.status === 'failed' && (
        <div className="ml-9 mt-2 flex gap-2">
          <button className="px-3 py-1 text-xs bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[#94A3B8] rounded-lg transition-colors">
            View Diff
          </button>
          <button className="px-3 py-1 text-xs bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[#94A3B8] rounded-lg transition-colors">
            Edit Test
          </button>
        </div>
      )}

      {testCase.status === 'pending' && (
        <div className="ml-9 mt-2">
          <button className="px-3 py-1 text-xs bg-[#8B5CF6] hover:bg-[#7C3AED] text-white rounded-lg transition-colors">
            Run Test
          </button>
        </div>
      )}
    </div>
  );
}
