import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { WorkflowBuilder } from '../workflow-builder/WorkflowBuilder';
import { useWorkflowStore } from '../../stores/workflowStore';

export function WorkflowBuilderScreen() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const { setWorkflow } = useWorkflowStore();

  useEffect(() => {
    // Initialize with sample workflow based on ID
    // In a real app, this would fetch the workflow from the API
    setWorkflow({
      id: id || 'new',
      name: id === 'new' ? 'Untitled Workflow' : 'Customer Support Pipeline',
      description: id === 'new' ? '' : 'Routes customer inquiries to appropriate support agents',
      nodes: [],
      edges: [],
    });
  }, [id, setWorkflow]);

  const handleBack = () => {
    navigate('/workflows');
  };

  return <WorkflowBuilder onBack={handleBack} />;
}
