import { useState } from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '../../App';

const settingsTabs = [
  'General',
  'API Keys',
  'Integrations',
  'Notifications',
  'Team',
  'Billing',
];

export function SettingsScreen() {
  const { theme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState('General');
  const [selfHealingEnabled, setSelfHealingEnabled] = useState(true);
  const [autoApplyFixes, setAutoApplyFixes] = useState(false);
  const [selectedTheme, setSelectedTheme] = useState<'light' | 'dark' | 'system'>(theme);

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setSelectedTheme(newTheme);
    if (newTheme !== 'system') {
      setTheme(newTheme);
    }
  };

  // Theme-aware classes
  const bgCard = theme === 'dark' ? 'bg-[#1A2642]' : 'bg-white';
  const borderCard = theme === 'dark' ? 'border-[rgba(212,175,55,0.2)]' : 'border-[#E5E7EB]';
  const textPrimary = theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]';
  const textSecondary = theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]';
  const bgHover = theme === 'dark' ? 'hover:bg-[rgba(212,175,55,0.1)]' : 'hover:bg-[#F9FAFB]';
  const bgInput = theme === 'dark' ? 'bg-[#0F1729]' : 'bg-[#F9FAFB]';
  const borderInput = theme === 'dark' ? 'border-[rgba(212,175,55,0.2)]' : 'border-[#E5E7EB]';

  return (
    <div className="p-6 flex gap-6 h-full">
      {/* Sidebar Tabs */}
      <div className="w-[200px] flex-shrink-0">
        <h1 className={`text-2xl font-semibold mb-6 ${textPrimary} font-greek`}>Settings</h1>
        <div className="space-y-1">
          {settingsTabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`w-full text-left px-4 py-2 rounded-lg text-sm transition-colors ${
                activeTab === tab
                  ? `bg-[rgba(212,175,55,0.15)] ${textPrimary} font-medium border-l-2 border-[#D4AF37]`
                  : `${textSecondary} ${bgHover}`
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Content Area */}
      <div className={`flex-1 ${bgCard} border ${borderCard} rounded-xl p-6 overflow-y-auto`}>
        {activeTab === 'General' && (
          <div className="space-y-6">
            <h2 className={`text-lg font-semibold ${textPrimary} uppercase tracking-wider`}>General Settings</h2>

            {/* Application Name */}
            <div>
              <label className={`block text-sm font-medium ${textPrimary} mb-2`}>Application Name</label>
              <input
                type="text"
                defaultValue="Labyrinth"
                className={`w-full ${bgInput} border ${borderInput} rounded-lg px-4 py-2 text-sm ${textPrimary} focus:border-[#D4AF37] focus:outline-none focus:ring-2 focus:ring-[rgba(212,175,55,0.3)]`}
              />
            </div>

            {/* Default Timezone */}
            <div>
              <label className={`block text-sm font-medium ${textPrimary} mb-2`}>Default Timezone</label>
              <select className={`w-full ${bgInput} border ${borderInput} rounded-lg px-4 py-2 text-sm ${textPrimary} focus:border-[#D4AF37] focus:outline-none focus:ring-2 focus:ring-[rgba(212,175,55,0.3)]`}>
                <option>UTC</option>
                <option>America/New_York</option>
                <option>America/Los_Angeles</option>
                <option>Europe/London</option>
                <option>Europe/Athens</option>
                <option>Asia/Tokyo</option>
              </select>
            </div>

            {/* Theme */}
            <div>
              <label className={`block text-sm font-medium ${textPrimary} mb-3`}>Theme</label>
              <div className="grid grid-cols-3 gap-3 max-w-lg">
                <ThemeOption
                  theme={theme}
                  icon={<Moon className="w-5 h-5" />}
                  label="Dark"
                  selected={selectedTheme === 'dark'}
                  onClick={() => handleThemeChange('dark')}
                />
                <ThemeOption
                  theme={theme}
                  icon={<Sun className="w-5 h-5" />}
                  label="Light"
                  selected={selectedTheme === 'light'}
                  onClick={() => handleThemeChange('light')}
                />
                <ThemeOption
                  theme={theme}
                  icon={<Monitor className="w-5 h-5" />}
                  label="System"
                  selected={selectedTheme === 'system'}
                  onClick={() => handleThemeChange('system')}
                />
              </div>
            </div>

            {/* Divider */}
            <div className={`h-px ${theme === 'dark' ? 'bg-[rgba(212,175,55,0.2)]' : 'bg-[#E5E7EB]'}`}></div>

            {/* Self-Healing Section */}
            <div>
              <h3 className={`text-base font-semibold ${textPrimary} mb-4 uppercase tracking-wider`}>Self-Healing (AIM)</h3>
              
              <div className="space-y-4">
                {/* Enable AI Self-Healing */}
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className={`text-sm font-medium ${textPrimary} mb-1`}>Enable AI Self-Healing</h4>
                    <p className={`text-xs ${textSecondary}`}>Automatically fix pipeline errors using AI</p>
                  </div>
                  <ToggleSwitch
                    enabled={selfHealingEnabled}
                    onChange={setSelfHealingEnabled}
                  />
                </div>

                {/* Auto-apply fixes */}
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className={`text-sm font-medium ${textPrimary} mb-1`}>Auto-apply fixes</h4>
                    <p className={`text-xs ${textSecondary}`}>Apply AI suggestions without confirmation</p>
                  </div>
                  <ToggleSwitch
                    enabled={autoApplyFixes}
                    onChange={setAutoApplyFixes}
                  />
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className={`h-px ${theme === 'dark' ? 'bg-[rgba(212,175,55,0.2)]' : 'bg-[#E5E7EB]'}`}></div>

            {/* Danger Zone */}
            <div>
              <h3 className="text-base font-semibold text-[#E07A5F] mb-4 uppercase tracking-wider">Danger Zone</h3>
              
              <div className="space-y-3 bg-[rgba(224,122,95,0.05)] border border-[rgba(224,122,95,0.2)] rounded-lg p-4">
                <DangerAction
                  theme={theme}
                  label="Delete All Pipelines"
                  buttonText="Delete All"
                />
                <DangerAction
                  theme={theme}
                  label="Reset All Agents"
                  buttonText="Reset"
                />
                <DangerAction
                  theme={theme}
                  label="Export Data"
                  buttonText="Export"
                  isDanger={false}
                />
              </div>
            </div>

            {/* Save Button */}
            <div className="flex justify-end pt-4">
              <button className="px-6 py-2 bg-gradient-to-r from-[#D4AF37] to-[#B8860B] hover:from-[#B8860B] hover:to-[#9A7510] text-white rounded-lg transition-all shadow-lg shadow-[rgba(212,175,55,0.25)] text-sm font-medium">
                Save Changes
              </button>
            </div>
          </div>
        )}

        {activeTab === 'API Keys' && (
          <div className="space-y-6">
            <h2 className={`text-lg font-semibold ${textPrimary} uppercase tracking-wider`}>API Keys</h2>
            <p className={`text-sm ${textSecondary}`}>Manage your API keys for external integrations</p>
            
            <div className="text-center py-12 text-[#64748B]">
              API Keys management interface
            </div>
          </div>
        )}

        {activeTab === 'Integrations' && (
          <div className="space-y-6">
            <h2 className={`text-lg font-semibold ${textPrimary} uppercase tracking-wider`}>Integrations</h2>
            <p className={`text-sm ${textSecondary}`}>Connect external services and tools</p>
            
            <div className="text-center py-12 text-[#64748B]">
              Integrations interface
            </div>
          </div>
        )}

        {activeTab === 'Notifications' && (
          <div className="space-y-6">
            <h2 className={`text-lg font-semibold ${textPrimary} uppercase tracking-wider`}>Notifications</h2>
            <p className={`text-sm ${textSecondary}`}>Configure how you receive alerts and updates</p>
            
            <div className="text-center py-12 text-[#64748B]">
              Notifications preferences
            </div>
          </div>
        )}

        {activeTab === 'Team' && (
          <div className="space-y-6">
            <h2 className={`text-lg font-semibold ${textPrimary} uppercase tracking-wider`}>Team</h2>
            <p className={`text-sm ${textSecondary}`}>Manage team members and permissions</p>
            
            <div className="text-center py-12 text-[#64748B]">
              Team management interface
            </div>
          </div>
        )}

        {activeTab === 'Billing' && (
          <div className="space-y-6">
            <h2 className={`text-lg font-semibold ${textPrimary} uppercase tracking-wider`}>Billing</h2>
            <p className={`text-sm ${textSecondary}`}>Manage your subscription and billing information</p>
            
            <div className="text-center py-12 text-[#64748B]">
              Billing interface
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ThemeOption({ 
  theme,
  icon, 
  label, 
  selected, 
  onClick 
}: { 
  theme: 'light' | 'dark';
  icon: React.ReactNode; 
  label: string; 
  selected: boolean; 
  onClick: () => void;
}) {
  const bgInput = theme === 'dark' ? 'bg-[#0F1729]' : 'bg-[#F9FAFB]';
  const borderInput = theme === 'dark' ? 'border-[rgba(212,175,55,0.2)]' : 'border-[#E5E7EB]';
  const textPrimary = theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]';
  const textSecondary = theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]';
  
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center justify-center gap-2 p-4 rounded-lg border transition-all ${
        selected
          ? `bg-[rgba(212,175,55,0.15)] border-[#D4AF37] ${textPrimary}`
          : `${bgInput} ${borderInput} ${textSecondary} hover:border-[#D4AF37]`
      }`}
    >
      {icon}
      <span className="text-sm font-medium">{label}</span>
      {selected && <div className="w-2 h-2 bg-[#D4AF37] rounded-full"></div>}
    </button>
  );
}

function ToggleSwitch({ enabled, onChange }: { enabled: boolean; onChange: (value: boolean) => void }) {
  return (
    <div className="flex items-center gap-2">
      <div 
        onClick={() => onChange(!enabled)}
        className={`relative w-12 h-6 rounded-full cursor-pointer transition-colors ${
          enabled ? 'bg-[#2C5F8D]' : 'bg-[rgba(100,116,139,0.3)]'
        }`}
      >
        <div 
          className={`absolute top-1 w-4 h-4 rounded-full transition-transform ${
            enabled ? 'translate-x-7 bg-[#D4AF37]' : 'translate-x-1 bg-white'
          }`}
        ></div>
      </div>
      <span className={`text-xs font-medium ${
        enabled ? 'text-[#2C5F8D]' : 'text-[#64748B]'
      }`}>
        {enabled ? 'ON' : 'OFF'}
      </span>
    </div>
  );
}

function DangerAction({ 
  theme,
  label, 
  buttonText, 
  isDanger = true 
}: { 
  theme: 'light' | 'dark';
  label: string; 
  buttonText: string; 
  isDanger?: boolean;
}) {
  const textPrimary = theme === 'dark' ? 'text-[#F5F5F0]' : 'text-[#0F172A]';
  const bgInput = theme === 'dark' ? 'bg-[#0F1729]' : 'bg-[#F9FAFB]';
  const bgHover = theme === 'dark' ? 'hover:bg-[rgba(212,175,55,0.1)]' : 'hover:bg-[#F3F4F6]';
  const textSecondary = theme === 'dark' ? 'text-[#94A3B8]' : 'text-[#64748B]';
  
  return (
    <div className="flex items-center justify-between py-2">
      <span className={`text-sm ${textPrimary}`}>{label}</span>
      <button className={`px-4 py-1.5 text-xs rounded-lg transition-colors ${
        isDanger
          ? 'bg-[#E07A5F] hover:bg-[#D66B50] text-white'
          : `${bgInput} ${bgHover} ${textSecondary}`
      }`}>
        {buttonText}
      </button>
    </div>
  );
}