import { useState } from 'react';
import { Settings, RefreshCw, Server, Activity } from 'lucide-react';
import axios from 'axios';

// API Base URL (relative path so it works through Docker proxy)
const API_URL = '/api';

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'settings'>('dashboard');
  const [syncStatus, setSyncStatus] = useState<string>('Idle');
  const [loading, setLoading] = useState(false);

  // --- ACTIONS ---
  const triggerSync = async () => {
    setLoading(true);
    setSyncStatus('Starting sync...');
    try {
      // Calls the Python Backend to start the sync
      const res = await axios.post(`${API_URL}/sync/run`, { type: 'movies' });
      
      if (res.data.success) {
        const stats = res.data.stats || { added: [], skipped: [] };
        setSyncStatus(`Sync Complete! Added: ${stats.added.length}, Skipped: ${stats.skipped.length}`);
      } else {
        setSyncStatus(`Failed: ${res.data.message}`);
      }
    } catch (err: any) {
      console.error(err);
      setSyncStatus('Error connecting to backend');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface text-white flex">
      {/* SIDEBAR */}
      <aside className="w-64 bg-background border-r border-gray-700 flex flex-col hidden md:flex">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-primary tracking-tight">MediaSync</h1>
        </div>
        <nav className="flex-1 px-4 space-y-2">
          <SidebarItem 
            icon={<Activity size={20} />} 
            label="Dashboard" 
            active={activeTab === 'dashboard'} 
            onClick={() => setActiveTab('dashboard')} 
          />
          <SidebarItem 
            icon={<Settings size={20} />} 
            label="Settings" 
            active={activeTab === 'settings'} 
            onClick={() => setActiveTab('settings')} 
          />
        </nav>
      </aside>

      {/* MOBILE HEADER (Visible only on small screens) */}
      <div className="md:hidden fixed top-0 w-full bg-background border-b border-gray-700 p-4 z-50 flex justify-between items-center">
         <h1 className="text-xl font-bold text-primary">MediaSync</h1>
      </div>

      {/* MAIN CONTENT */}
      <main className="flex-1 p-8 mt-14 md:mt-0 overflow-y-auto">
        {activeTab === 'dashboard' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <h2 className="text-3xl font-bold mb-8">Dashboard</h2>
            
            {/* Status Card */}
            <div className="bg-background rounded-xl p-6 border border-gray-700 shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Server className="text-primary" /> Service Status
                </h3>
                <span className="px-3 py-1 bg-green-900 text-green-300 text-sm rounded-full">
                  System Online
                </span>
              </div>
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row justify-between items-center bg-surface p-4 rounded-lg gap-4">
                  <div className="text-center sm:text-left">
                    <p className="text-gray-400 text-sm">Last Sync Status</p>
                    <p className="font-medium text-gray-200">{syncStatus}</p>
                  </div>
                  <button 
                    onClick={triggerSync}
                    disabled={loading}
                    className={`flex items-center gap-2 px-6 py-2 rounded-md font-medium transition-colors ${
                      loading ? 'bg-gray-600 cursor-not-allowed' : 'bg-primary hover:bg-primary-hover'
                    }`}
                  >
                    <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
                    {loading ? 'Syncing...' : 'Sync Now'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="max-w-4xl mx-auto">
             <h2 className="text-3xl font-bold mb-8">Settings</h2>
             <div className="bg-background p-12 rounded-xl border border-gray-700 text-center text-gray-400">
               <Settings className="mx-auto mb-4 w-12 h-12 text-gray-600" />
               <h3 className="text-lg font-semibold text-gray-300">Configuration</h3>
               <p className="mt-2">Use the API to configure settings for now.</p>
               <p className="text-sm mt-4 text-gray-500">Edit /opt/media-sync-app/config/media_sync.db directly or use cURL.</p>
             </div>
          </div>
        )}
      </main>
    </div>
  );
}

// Helper Component for Sidebar Buttons
function SidebarItem({ icon, label, active, onClick }: any) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
        active 
          ? 'bg-primary/20 text-primary border-r-2 border-primary' 
          : 'text-gray-400 hover:bg-gray-700 hover:text-white'
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </button>
  );
}

export default App;