import React from 'react';
import { Plus, ChevronUp, ChevronDown, Trash2 } from 'lucide-react';

interface ConditionEditorProps {
  isDark: boolean;
  nodeName: string;
}

interface ElseIfCondition {
  id: number;
  condition: string;
}

export function ConditionEditor({ isDark, nodeName }: ConditionEditorProps) {
  const [ifCondition, setIfCondition] = React.useState('<response> === true');
  const [elseIfs, setElseIfs] = React.useState<ElseIfCondition[]>([]);
  const [elseCondition, setElseCondition] = React.useState('');

  const addElseIf = () => {
    setElseIfs([...elseIfs, { id: Date.now(), condition: '<response> === true' }]);
  };

  const removeElseIf = (id: number) => {
    setElseIfs(elseIfs.filter(item => item.id !== id));
  };

  const moveElseIfUp = (index: number) => {
    if (index === 0) return;
    const newElseIfs = [...elseIfs];
    [newElseIfs[index - 1], newElseIfs[index]] = [newElseIfs[index], newElseIfs[index - 1]];
    setElseIfs(newElseIfs);
  };

  const moveElseIfDown = (index: number) => {
    if (index === elseIfs.length - 1) return;
    const newElseIfs = [...elseIfs];
    [newElseIfs[index], newElseIfs[index + 1]] = [newElseIfs[index + 1], newElseIfs[index]];
    setElseIfs(newElseIfs);
  };

  const updateElseIfCondition = (id: number, condition: string) => {
    setElseIfs(elseIfs.map(item => item.id === id ? { ...item, condition } : item));
  };

  return (
    <div className="p-4 space-y-4">
      {/* If Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>if</span>
          <div className="flex items-center gap-1">
            <button 
              onClick={addElseIf}
              className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded`}
              title="Add else if"
            >
              <Plus className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
            </button>
            <button className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded`}>
              <ChevronUp className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
            </button>
            <button className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded`}>
              <ChevronDown className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
            </button>
            <button className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded`}>
              <Trash2 className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
            </button>
          </div>
        </div>
        <textarea
          value={ifCondition}
          onChange={(e) => setIfCondition(e.target.value)}
          className={`w-full ${isDark ? 'bg-[#0a0a0a] border-gray-700 text-gray-300' : 'bg-gray-50 border-gray-200 text-gray-900'} border rounded p-3 font-mono text-xs resize-none focus:outline-none focus:border-blue-500`}
          rows={3}
          placeholder="Enter condition..."
        />
      </div>

      {/* Dynamic Else If Sections */}
      {elseIfs.map((elseIf, index) => (
        <div key={elseIf.id}>
          <div className="flex items-center justify-between mb-3">
            <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>else if</span>
            <div className="flex items-center gap-1">
              <button 
                onClick={addElseIf}
                className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded`}
                title="Add else if"
              >
                <Plus className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
              </button>
              <button 
                onClick={() => moveElseIfUp(index)}
                className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded ${index === 0 ? 'opacity-50' : ''}`}
                disabled={index === 0}
              >
                <ChevronUp className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
              </button>
              <button 
                onClick={() => moveElseIfDown(index)}
                className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded ${index === elseIfs.length - 1 ? 'opacity-50' : ''}`}
                disabled={index === elseIfs.length - 1}
              >
                <ChevronDown className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
              </button>
              <button 
                onClick={() => removeElseIf(elseIf.id)}
                className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded`}
              >
                <Trash2 className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
              </button>
            </div>
          </div>
          <textarea
            value={elseIf.condition}
            onChange={(e) => updateElseIfCondition(elseIf.id, e.target.value)}
            className={`w-full ${isDark ? 'bg-[#0a0a0a] border-gray-700 text-gray-300' : 'bg-gray-50 border-gray-200 text-gray-900'} border rounded p-3 font-mono text-xs resize-none focus:outline-none focus:border-blue-500`}
            rows={3}
            placeholder="Enter condition..."
          />
        </div>
      ))}

      {/* Else Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>else</span>
          <div className="flex items-center gap-1">
            <button className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded`}>
              <Plus className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
            </button>
            <button className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded`}>
              <ChevronUp className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
            </button>
            <button className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded`}>
              <ChevronDown className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
            </button>
            <button className={`p-1 ${isDark ? 'hover:bg-[#2a2a2a]' : 'hover:bg-gray-100'} rounded`}>
              <Trash2 className={`w-3.5 h-3.5 ${isDark ? 'text-gray-400' : 'text-gray-600'}`} />
            </button>
          </div>
        </div>
        <textarea
          value={elseCondition}
          onChange={(e) => setElseCondition(e.target.value)}
          className={`w-full ${isDark ? 'bg-[#0a0a0a] border-gray-700 text-gray-300' : 'bg-gray-50 border-gray-200 text-gray-900'} border rounded p-3 font-mono text-xs resize-none focus:outline-none focus:border-blue-500`}
          rows={3}
          placeholder="Default action (optional)..."
        />
      </div>
    </div>
  );
}