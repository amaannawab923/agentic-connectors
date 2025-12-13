import { useState, createContext, useContext } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardContent } from './components/DashboardContent';
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
  theme: 'light',
  setTheme: () => {},
});

export const useTheme = () => useContext(ThemeContext);

export default function App() {
  const [currentPage, setCurrentPage] = useState('Dashboard');
  const [theme, setTheme] = useState<Theme>('light');

  // Render the appropriate screen based on currentPage
  const renderContent = () => {
    switch (currentPage) {
      case 'Dashboard':
        return <DashboardContent />;
      case 'Pipelines':
        return <PipelinesScreen />;
      case 'Triggers':
        return <TriggersScreen />;
      case 'Pipeline Runs':
        return <PipelineRunsScreen />;
      case 'Agentic Assets':
        return <AgenticAssetsScreen />;
      case 'Training':
        return <TrainingScreen />;
      case 'Settings':
        return <SettingsScreen />;
      default:
        return <DashboardContent />;
    }
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      <div className={`flex h-screen ${
        theme === 'dark' 
          ? 'bg-[#0F1729] text-[#F5F5F0]' 
          : 'bg-[#F9FAFB] text-[#0F172A]'
      } overflow-hidden`}>
        <Sidebar currentPage={currentPage} onNavigate={setCurrentPage} />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header currentPage={currentPage} />
          <main className="flex-1 overflow-y-auto">
            {renderContent()}
          </main>
        </div>
      </div>
    </ThemeContext.Provider>
  );
}