import { ArrowLeft, Pencil, Save, Play, ChevronDown, Rocket } from 'lucide-react';
import { useState } from 'react';
import { useTheme } from '../../App';

interface BuilderHeaderProps {
  workflowName: string;
  workflowIcon: string;
  onBack: () => void;
  onSave: () => void;
  onTest: () => void;
  onPublish: () => void;
  onNameEdit?: (name: string) => void;
}

export function BuilderHeader({
  workflowName,
  workflowIcon,
  onBack,
  onSave,
  onTest,
  onPublish,
  onNameEdit,
}: BuilderHeaderProps) {
  const { theme } = useTheme();
  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(workflowName);
  const [showTestMenu, setShowTestMenu] = useState(false);

  const handleNameSave = () => {
    if (editedName.trim()) {
      onNameEdit?.(editedName);
      setIsEditing(false);
    }
  };

  return (
    <div className={`h-14 flex items-center justify-between px-6 border-b ${
      theme === 'dark'
        ? 'bg-[#0F172A] border-[rgba(148,163,184,0.1)]'
        : 'bg-white border-[#E2E8F0]'
    }`}>
      {/* Left: Back + Name */}
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
            theme === 'dark'
              ? 'text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)]'
              : 'text-[#64748B] hover:bg-[#F9FAFB]'
          }`}
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>

        <div className="flex items-center gap-3">
          {/* Icon */}
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white shadow-lg">
            {workflowIcon}
          </div>

          {/* Name */}
          {isEditing ? (
            <input
              type="text"
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              onBlur={handleNameSave}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleNameSave();
                if (e.key === 'Escape') {
                  setEditedName(workflowName);
                  setIsEditing(false);
                }
              }}
              className={`text-lg font-semibold px-2 py-1 rounded border outline-none ${
                theme === 'dark'
                  ? 'bg-[#1E293B] border-[rgba(148,163,184,0.2)] text-[#F5F5F0]'
                  : 'bg-[#F9FAFB] border-[#E2E8F0] text-[#0F172A]'
              }`}
              autoFocus
            />
          ) : (
            <div className="flex items-center gap-2">
              <h1 className={`text-lg font-semibold ${
                theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
              }`}>
                {workflowName}
              </h1>
              <button
                onClick={() => setIsEditing(true)}
                className={`p-1 rounded transition-colors ${
                  theme === 'dark'
                    ? 'hover:bg-[rgba(255,255,255,0.05)]'
                    : 'hover:bg-[#F9FAFB]'
                }`}
              >
                <Pencil className="w-4 h-4 text-[#64748B]" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Right: Action Buttons */}
      <div className="flex items-center gap-3">
        {/* Save Button */}
        <button
          onClick={onSave}
          className={`flex items-center gap-2 px-4 py-2 text-sm border rounded-lg transition-colors ${
            theme === 'dark'
              ? 'border-[rgba(148,163,184,0.2)] text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)]'
              : 'border-[#E2E8F0] text-[#64748B] hover:bg-[#F9FAFB]'
          }`}
        >
          <Save className="w-4 h-4" />
          Save
        </button>

        {/* Test Button with Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowTestMenu(!showTestMenu)}
            className={`flex items-center gap-2 px-4 py-2 text-sm border rounded-lg transition-colors ${
              theme === 'dark'
                ? 'border-[rgba(148,163,184,0.2)] text-[#94A3B8] hover:bg-[rgba(255,255,255,0.05)]'
                : 'border-[#E2E8F0] text-[#64748B] hover:bg-[#F9FAFB]'
            }`}
          >
            <Play className="w-4 h-4" />
            Test
            <ChevronDown className="w-4 h-4" />
          </button>

          {/* Test Dropdown */}
          {showTestMenu && (
            <div
              className={`absolute right-0 mt-2 w-56 rounded-lg shadow-xl border z-50 ${
                theme === 'dark'
                  ? 'bg-[#1E293B] border-[rgba(148,163,184,0.1)]'
                  : 'bg-white border-[#E2E8F0]'
              }`}
            >
              <button
                onClick={() => {
                  onTest();
                  setShowTestMenu(false);
                }}
                className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                  theme === 'dark'
                    ? 'text-[#F5F5F0] hover:bg-[rgba(255,255,255,0.05)]'
                    : 'text-[#0F172A] hover:bg-[#F9FAFB]'
                }`}
              >
                Run Full Workflow
              </button>
              <button
                className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                  theme === 'dark'
                    ? 'text-[#F5F5F0] hover:bg-[rgba(255,255,255,0.05)]'
                    : 'text-[#0F172A] hover:bg-[#F9FAFB]'
                }`}
              >
                Run from Selected Node
              </button>
              <button
                className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                  theme === 'dark'
                    ? 'text-[#F5F5F0] hover:bg-[rgba(255,255,255,0.05)]'
                    : 'text-[#0F172A] hover:bg-[#F9FAFB]'
                }`}
              >
                Run with Test Input
              </button>
            </div>
          )}
        </div>

        {/* Publish Button */}
        <button
          onClick={onPublish}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors shadow-lg shadow-purple-500/25"
        >
          <Rocket className="w-4 h-4" />
          Publish
        </button>
      </div>
    </div>
  );
}
