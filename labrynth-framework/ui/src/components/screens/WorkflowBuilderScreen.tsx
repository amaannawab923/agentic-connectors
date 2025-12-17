import { useNavigate } from 'react-router-dom';
import { WorkflowBuilderV2 } from '../workflow-builder-v2';

export function WorkflowBuilderScreen() {
  const navigate = useNavigate();

  const handleBack = () => {
    navigate('/workflows');
  };

  return <WorkflowBuilderV2 onBack={handleBack} />;
}
