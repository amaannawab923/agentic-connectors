import { useState, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardContent } from './components/DashboardContent';
import { WorkflowsScreen } from './components/screens/WorkflowsScreen';
import { WorkflowBuilderScreen } from './components/screens/WorkflowBuilderScreen';
import { PipelinesScreen } from './components/screens/PipelinesScreen';
import { TriggersScreen } from './components/screens/TriggersScreen';
import { PipelineRunsScreen } from './components/screens/PipelineRunsScreen';
import { AgenticAssetsScreen } from './components/screens/AgenticAssetsScreen';
import { TrainingScreen } from './components/screens/TrainingScreen';
import { SettingsScreen } from './components/screens/SettingsScreen';

// Theme Context
type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

export const ThemeContext = createContext<ThemeContextType>({
  theme: 'dark',
  setTheme: () => {},
});

export const useTheme = () => useContext(ThemeContext);

// Route configuration (excluding workflow builder which has special layout)
export const routes = [
  { path: '/', name: 'Dashboard', element: <DashboardContent /> },
  { path: '/workflows', name: 'Workflows', element: <WorkflowsScreen /> },
  { path: '/pipelines', name: 'Pipelines', element: <PipelinesScreen /> },
  { path: '/triggers', name: 'Triggers', element: <TriggersScreen /> },
  { path: '/runs', name: 'Pipeline Runs', element: <PipelineRunsScreen /> },
  { path: '/agents', name: 'Agentic Assets', element: <AgenticAssetsScreen /> },
  { path: '/training', name: 'Training', element: <TrainingScreen /> },
  { path: '/settings', name: 'Settings', element: <SettingsScreen /> },
];

function AppLayout() {
  const { theme } = useTheme();
  const location = useLocation();

  // Check if we're on the workflow builder page (fullscreen without sidebar/header)
  const isWorkflowBuilder = location.pathname.startsWith('/workflows/');

  if (isWorkflowBuilder) {
    return (
      <div className={`h-screen ${
        theme === 'dark'
          ? 'bg-[#0F1729] text-[#F5F5F0]'
          : 'bg-[#F9FAFB] text-[#0F172A]'
      } overflow-hidden`}>
        <Routes>
          <Route path="/workflows/:id" element={<WorkflowBuilderScreen />} />
        </Routes>
      </div>
    );
  }

  return (
    <div className={`flex h-screen ${
      theme === 'dark'
        ? 'bg-[#0F1729] text-[#F5F5F0]'
        : 'bg-[#F9FAFB] text-[#0F172A]'
    } overflow-hidden`}>
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            {routes.map((route) => (
              <Route key={route.path} path={route.path} element={route.element} />
            ))}
            {/* Redirect unknown routes to dashboard */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = useState<Theme>('dark');

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </ThemeContext.Provider>
  );
}
