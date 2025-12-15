import { X } from 'lucide-react';
import { useState } from 'react';
import { useTheme } from '../../App';

interface CreateWorkflowModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: { name: string; description: string; icon: string }) => void;
}

export function CreateWorkflowModal({ isOpen, onClose, onCreate }: CreateWorkflowModalProps) {
  const { theme } = useTheme();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [icon, setIcon] = useState('🔄');
  const [startOption, setStartOption] = useState<'blank' | 'template'>('blank');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = () => {
    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    onCreate({ name, description, icon });

    // Reset form
    setName('');
    setDescription('');
    setIcon('🔄');
    setError('');
    onClose();
  };

  const emojiOptions = ['🔄', '📊', '🧠', '📝', '💬', '📧', '⚡', '🔗', '🎯', '🚀'];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.6)' }}
      onClick={onClose}
    >
      <div
        className={`w-full max-w-md rounded-2xl shadow-2xl ${
          theme === 'dark' ? 'bg-[#1A2642]' : 'bg-white'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`flex items-center justify-between p-6 border-b ${
          theme === 'dark' ? 'border-[rgba(212,175,55,0.2)]' : 'border-[#E5E7EB]'
        }`}>
          <h2 className={`text-xl font-semibold ${
            theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
          }`}>
            Create New Workflow
          </h2>
          <button
            onClick={onClose}
            className={`p-1.5 rounded-lg transition-colors ${
              theme === 'dark'
                ? 'hover:bg-[rgba(212,175,55,0.1)]'
                : 'hover:bg-[#F9FAFB]'
            }`}
          >
            <X className="w-5 h-5" style={{ color: theme === 'dark' ? '#94A3B8' : '#64748B' }} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Icon Picker */}
          <div>
            <label className={`block text-sm font-medium mb-2 ${
              theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
            }`}>
              Icon
            </label>
            <div className="flex gap-2 flex-wrap">
              {emojiOptions.map((emoji) => (
                <button
                  key={emoji}
                  onClick={() => setIcon(emoji)}
                  className={`w-12 h-12 rounded-lg text-2xl transition-all ${
                    icon === emoji
                      ? 'bg-gradient-to-br from-[#D4AF37] to-[#B8860B] shadow-lg'
                      : theme === 'dark'
                      ? 'bg-[#0F1729] hover:bg-[rgba(212,175,55,0.1)]'
                      : 'bg-[#F9FAFB] hover:bg-[#F1F5F9]'
                  }`}
                >
                  {emoji}
                </button>
              ))}
            </div>
          </div>

          {/* Name Input */}
          <div>
            <label className={`block text-sm font-medium mb-2 ${
              theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
            }`}>
              Name <span className="text-[#EF4444]">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setError('');
              }}
              placeholder="Enter workflow name..."
              maxLength={100}
              className={`w-full px-4 py-2.5 rounded-lg border text-sm transition-colors ${
                error
                  ? 'border-[#EF4444] focus:border-[#EF4444]'
                  : theme === 'dark'
                  ? 'bg-[#0F1729] border-[rgba(212,175,55,0.2)] text-[#F5F5F0] focus:border-[#D4AF37]'
                  : 'bg-[#F9FAFB] border-[#E5E7EB] text-[#0F172A] focus:border-[#2C5F8D]'
              } outline-none focus:ring-2 ${
                error
                  ? 'focus:ring-[rgba(239,68,68,0.2)]'
                  : 'focus:ring-[rgba(212,175,55,0.2)]'
              }`}
            />
            {error && (
              <p className="text-xs text-[#EF4444] mt-1">{error}</p>
            )}
          </div>

          {/* Description Textarea */}
          <div>
            <label className={`block text-sm font-medium mb-2 ${
              theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
            }`}>
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this workflow does..."
              maxLength={500}
              rows={3}
              className={`w-full px-4 py-2.5 rounded-lg border text-sm resize-none transition-colors ${
                theme === 'dark'
                  ? 'bg-[#0F1729] border-[rgba(212,175,55,0.2)] text-[#F5F5F0] focus:border-[#D4AF37]'
                  : 'bg-[#F9FAFB] border-[#E5E7EB] text-[#0F172A] focus:border-[#2C5F8D]'
              } outline-none focus:ring-2 focus:ring-[rgba(212,175,55,0.2)]`}
            />
            <div className={`text-xs text-right mt-1 ${
              theme === 'dark' ? 'text-[#64748B]' : 'text-[#94A3B8]'
            }`}>
              {description.length}/500
            </div>
          </div>

          {/* Divider */}
          <div className={`h-px ${
            theme === 'dark' ? 'bg-[rgba(212,175,55,0.2)]' : 'bg-[#E5E7EB]'
          }`}></div>

          {/* Start Options */}
          <div className="space-y-3">
            {/* Blank Option */}
            <label
              className={`flex items-start gap-3 p-4 rounded-lg border cursor-pointer transition-all ${
                startOption === 'blank'
                  ? 'border-[#D4AF37] bg-[rgba(212,175,55,0.1)]'
                  : theme === 'dark'
                  ? 'border-[rgba(212,175,55,0.2)] hover:border-[rgba(212,175,55,0.4)]'
                  : 'border-[#E5E7EB] hover:border-[#CBD5E1]'
              }`}
            >
              <input
                type="radio"
                name="startOption"
                value="blank"
                checked={startOption === 'blank'}
                onChange={(e) => setStartOption(e.target.value as 'blank')}
                className="mt-0.5"
              />
              <div className="flex-1">
                <div className={`font-medium text-sm mb-1 ${
                  theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
                }`}>
                  Start from Blank
                </div>
                <div className={`text-xs ${
                  theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'
                }`}>
                  Create an empty workflow canvas
                </div>
              </div>
            </label>

            {/* Template Option */}
            <label
              className={`flex items-start gap-3 p-4 rounded-lg border opacity-50 cursor-not-allowed ${
                theme === 'dark'
                  ? 'border-[rgba(212,175,55,0.2)]'
                  : 'border-[#E5E7EB]'
              }`}
            >
              <input
                type="radio"
                name="startOption"
                value="template"
                disabled
                className="mt-0.5"
              />
              <div className="flex-1">
                <div className={`font-medium text-sm mb-1 flex items-center gap-2 ${
                  theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
                }`}>
                  Use Template
                  <span className="px-2 py-0.5 bg-[rgba(212,175,55,0.15)] text-[#D4AF37] text-xs rounded-full">
                    Coming Soon
                  </span>
                </div>
                <div className={`text-xs ${
                  theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'
                }`}>
                  Start with a pre-built workflow
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className={`flex items-center justify-end gap-3 p-6 border-t ${
          theme === 'dark' ? 'border-[rgba(212,175,55,0.2)]' : 'border-[#E5E7EB]'
        }`}>
          <button
            onClick={onClose}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              theme === 'dark'
                ? 'bg-transparent border border-[rgba(212,175,55,0.3)] text-[#F5F5F0] hover:bg-[rgba(212,175,55,0.1)]'
                : 'bg-transparent border border-[#E5E7EB] text-[#0F172A] hover:bg-[#F9FAFB]'
            }`}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim()}
            className={`px-4 py-2 rounded-lg text-sm font-medium text-white transition-all shadow-lg ${
              name.trim()
                ? 'bg-gradient-to-r from-[#D4AF37] to-[#B8860B] hover:from-[#B8860B] hover:to-[#9A7510] shadow-[rgba(212,175,55,0.25)]'
                : 'bg-gray-400 cursor-not-allowed'
            }`}
          >
            Create Workflow
          </button>
        </div>
      </div>
    </div>
  );
}
