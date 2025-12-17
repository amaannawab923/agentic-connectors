import { Search, Filter, ArrowUpDown, Plus } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../../App';
import { mockWorkflows } from '../../data/mockWorkflows';
import { WorkflowCard } from '../workflows/WorkflowCard';
import { CreateWorkflowModal } from '../workflows/CreateWorkflowModal';

export function WorkflowsScreen() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'running' | 'draft' | 'failed'>('all');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const tabs = [
    { key: 'all', label: 'All', count: mockWorkflows.length },
    { key: 'running', label: 'Running', count: mockWorkflows.filter(w => w.status === 'running').length },
    { key: 'draft', label: 'Draft', count: mockWorkflows.filter(w => w.status === 'draft').length },
    { key: 'failed', label: 'Failed', count: mockWorkflows.filter(w => w.status === 'failed').length },
  ];

  const filteredWorkflows = mockWorkflows.filter(workflow => {
    // Filter by tab
    if (activeTab !== 'all' && workflow.status !== activeTab) return false;

    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        workflow.name.toLowerCase().includes(query) ||
        workflow.description.toLowerCase().includes(query) ||
        workflow.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    return true;
  });

  const handleCreateWorkflow = (data: { name: string; description: string; icon: string }) => {
    console.log('Creating workflow:', data);
    // In a real app, this would create the workflow and navigate to the builder
    const newId = `wf-${Date.now()}`;
    navigate(`/workflows/${newId}`);
  };

  const handleWorkflowClick = (id: string) => {
    navigate(`/workflows/${id}`);
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-6 space-y-6">
        {/* Page Header */}
        <div>
          <h1 className={`text-2xl font-semibold mb-1 ${
            theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
          }`}>
            Workflows
          </h1>
          <p className={`text-sm ${
            theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'
          }`}>
            Build visual pipelines by connecting agents together
          </p>
        </div>

        {/* Search & Actions Bar */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="flex-1 max-w-md relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search workflows..."
              className={`w-full pl-10 pr-4 py-2.5 rounded-lg border text-sm transition-colors ${
                theme === 'dark'
                  ? 'bg-[#0F1729] border-[rgba(212,175,55,0.2)] text-[#F5F5F0] focus:border-[#D4AF37]'
                  : 'bg-[#F9FAFB] border-[#E5E7EB] text-[#0F172A] focus:border-[#2C5F8D]'
              } outline-none focus:ring-2 focus:ring-[rgba(212,175,55,0.2)]`}
            />
          </div>

          {/* Filter Button */}
          <button className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
            theme === 'dark'
              ? 'bg-[#0F1729] border-[rgba(212,175,55,0.2)] text-[#F5F5F0] hover:border-[#D4AF37]'
              : 'bg-[#F9FAFB] border-[#E5E7EB] text-[#0F172A] hover:border-[#2C5F8D]'
          }`}>
            <Filter className="w-4 h-4" />
            Filter
          </button>

          {/* Sort Button */}
          <button className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
            theme === 'dark'
              ? 'bg-[#0F1729] border-[rgba(212,175,55,0.2)] text-[#F5F5F0] hover:border-[#D4AF37]'
              : 'bg-[#F9FAFB] border-[#E5E7EB] text-[#0F172A] hover:border-[#2C5F8D]'
          }`}>
            <ArrowUpDown className="w-4 h-4" />
            Sort
          </button>

          {/* Create Button */}
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-white bg-gradient-to-r from-[#D4AF37] to-[#B8860B] hover:from-[#B8860B] hover:to-[#9A7510] transition-all shadow-lg shadow-[rgba(212,175,55,0.25)]"
          >
            <Plus className="w-4 h-4" />
            Create Workflow
          </button>
        </div>

        {/* Status Tabs */}
        <div className="flex items-center gap-6 border-b" style={{
          borderColor: theme === 'dark' ? 'rgba(212,175,55,0.2)' : '#E5E7EB'
        }}>
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`pb-3 text-sm font-medium transition-colors relative ${
                activeTab === tab.key
                  ? theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
                  : theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'
              } hover:text-[#D4AF37]`}
            >
              {tab.label} ({tab.count})
              {activeTab === tab.key && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#D4AF37]"></div>
              )}
            </button>
          ))}
        </div>

        {/* Workflows Grid */}
        {filteredWorkflows.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {/* Create New Card */}
            <div
              onClick={() => setIsCreateModalOpen(true)}
              className={`rounded-xl p-5 border-2 border-dashed cursor-pointer transition-all hover:border-[#D4AF37] hover:bg-[rgba(212,175,55,0.05)] flex flex-col items-center justify-center min-h-[240px] ${
                theme === 'dark'
                  ? 'border-[rgba(212,175,55,0.3)]'
                  : 'border-[#CBD5E1]'
              }`}
            >
              <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 ${
                theme === 'dark'
                  ? 'bg-[rgba(212,175,55,0.1)]'
                  : 'bg-[rgba(44,95,141,0.1)]'
              }`}>
                <Plus className="w-8 h-8 text-[#D4AF37]" />
              </div>
              <h3 className={`text-base font-semibold mb-2 ${
                theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
              }`}>
                Create New Workflow
              </h3>
              <p className={`text-xs text-center ${
                theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'
              }`}>
                Start from scratch or use a template
              </p>
            </div>

            {/* Workflow Cards */}
            {filteredWorkflows.map((workflow) => (
              <WorkflowCard
                key={workflow.id}
                workflow={workflow}
                onClick={() => handleWorkflowClick(workflow.id)}
              />
            ))}
          </div>
        ) : (
          /* Empty State */
          <div className="flex flex-col items-center justify-center py-16">
            <div className="text-6xl mb-4">🔗</div>
            <h3 className={`text-lg font-semibold mb-2 ${
              theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]'
            }`}>
              {searchQuery ? 'No workflows found' : 'No workflows yet'}
            </h3>
            <p className={`text-sm mb-6 max-w-md text-center ${
              theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'
            }`}>
              {searchQuery
                ? 'Try adjusting your search or filters'
                : 'Create your first workflow to start building AI-powered automation pipelines'}
            </p>
            {!searchQuery && (
              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-medium text-white bg-gradient-to-r from-[#D4AF37] to-[#B8860B] hover:from-[#B8860B] hover:to-[#9A7510] transition-all shadow-lg shadow-[rgba(212,175,55,0.25)]"
              >
                <Plus className="w-5 h-5" />
                Create Your First Workflow
              </button>
            )}
          </div>
        )}

        {/* Pagination */}
        {filteredWorkflows.length > 0 && (
          <div className="flex items-center justify-between pt-4">
            <div className={`text-sm ${
              theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]'
            }`}>
              Showing 1-{filteredWorkflows.length} of {filteredWorkflows.length} workflows
            </div>
            <div className="flex items-center gap-2">
              <button className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                theme === 'dark'
                  ? 'bg-[rgba(212,175,55,0.1)] text-[#D4AF37] hover:bg-[rgba(212,175,55,0.2)]'
                  : 'bg-[rgba(44,95,141,0.1)] text-[#2C5F8D] hover:bg-[rgba(44,95,141,0.2)]'
              }`}>
                1
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Create Workflow Modal */}
      <CreateWorkflowModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreateWorkflow}
      />
    </div>
  );
}
