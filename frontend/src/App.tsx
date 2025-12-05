import { useEffect, useMemo, useState } from 'react';
import { Settings, RefreshCw, Server, Activity, Shield, Wifi, HardDrive, TestTube2, Save, Trash2 } from 'lucide-react';
import axios from 'axios';

const API_URL = '/api';

type WatchItem = {
  title: string;
  rating_key: string;
  poster?: string;
  year?: string;
  type?: string;
  status?: string;
  summary?: string;
};

type Watchlists = { mine: WatchItem[]; friends: WatchItem[] };

type Config = {
  plex: { url: string; token: string; rss_my_url: string; rss_friend_url: string; auto_sync_enabled: boolean; auto_sync_interval_seconds: number };
  radarr: { url: string; api_key: string; quality_profile_id: number; root_folder_path: string };
  sonarr: { url: string; api_key: string; quality_profile_id: number; root_folder_path: string };
};

const statusColor = (status?: string) => {
  if (status === 'downloaded') return 'bg-green-900 text-green-200';
  if (status === 'added') return 'bg-yellow-900 text-yellow-200';
  return 'bg-gray-800 text-gray-300';
};

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'settings'>('dashboard');
  const [watchlists, setWatchlists] = useState<Watchlists>({ mine: [], friends: [] });
  const [syncStatus, setSyncStatus] = useState<string>('Idle');
  const [loading, setLoading] = useState(false);
  const [pulling, setPulling] = useState(false);
  const [config, setConfig] = useState<Config | null>(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<{ [k: string]: boolean }>({});

  const fetchConfig = async () => {
    const res = await axios.get(`${API_URL}/config`);
    setConfig(res.data);
  };

  const fetchWatchlists = async () => {
    const res = await axios.get(`${API_URL}/watchlists`);
    setWatchlists(res.data);
  };

  useEffect(() => {
    fetchConfig();
    fetchWatchlists();
  }, []);

  const pullWatchlists = async () => {
    setPulling(true);
    setSyncStatus('Pulling watchlists from Plex...');
    try {
      await fetchWatchlists();
      setSyncStatus('Watchlists refreshed from Plex');
    } catch (err: any) {
      console.error(err);
      setSyncStatus('Failed to pull watchlists');
    } finally {
      setPulling(false);
    }
  };

  const triggerPush = async () => {
    setLoading(true);
    setSyncStatus('Pushing to Radarr/Sonarr...');
    try {
      const res = await axios.post(`${API_URL}/sync/run`);
      if (res.data.success) {
        const stats = res.data.stats || { added: [], skipped: [] };
        setSyncStatus(`Push complete. Added: ${stats.added.length}, Skipped: ${stats.skipped.length}`);
        fetchWatchlists();
      } else {
        setSyncStatus(`Push failed: ${res.data.message}`);
      }
    } catch (err: any) {
      console.error(err);
      setSyncStatus('Error connecting to backend');
    } finally {
      setLoading(false);
    }
  };

  const handleInput = (path: string, value: any) => {
    if (!config) return;
    const [section, field] = path.split('.');
    setConfig({
      ...config,
      [section]: {
        ...(config as any)[section],
        [field]: value,
      },
    });
  };

  const saveConfig = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await axios.put(`${API_URL}/config`, config);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const testService = async (service_type: 'plex' | 'radarr' | 'sonarr') => {
    if (!config) return;
    setTesting((prev) => ({ ...prev, [service_type]: true }));
    try {
      const payload = {
        service_type,
        url: (config as any)[service_type].url,
        api_key: (config as any)[service_type].api_key || (service_type === 'plex' ? config.plex.token : ''),
      };
      await axios.post(`${API_URL}/services/test`, payload);
    } catch (err) {
      console.error(err);
    } finally {
      setTesting((prev) => ({ ...prev, [service_type]: false }));
    }
  };

  const gridEmpty = useMemo(() => watchlists.mine.length === 0 && watchlists.friends.length === 0, [watchlists]);

  const removeWatchlistItem = async (rating_key: string) => {
    try {
      const res = await axios.post(`${API_URL}/watchlist/remove`, { rating_key });
      if (res.data?.success) {
        await fetchWatchlists();
        setSyncStatus('Item removed from Plex watchlist');
      } else {
        setSyncStatus('Failed to remove from watchlist');
      }
    } catch (err) {
      console.error(err);
      setSyncStatus('Failed to remove from watchlist');
    }
  };

  return (
    <div className="min-h-screen bg-surface text-white flex">
      <aside className="w-64 bg-background border-r border-gray-800 flex flex-col hidden md:flex">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-primary tracking-tight">MediaSync</h1>
        </div>
        <nav className="flex-1 px-4 space-y-2">
          <SidebarItem icon={<Activity size={20} />} label="Dashboard" active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} />
          <SidebarItem icon={<Settings size={20} />} label="Settings" active={activeTab === 'settings'} onClick={() => setActiveTab('settings')} />
        </nav>
      </aside>

      <div className="md:hidden fixed top-0 w-full bg-background border-b border-gray-800 p-4 z-50 flex justify-between items-center">
        <h1 className="text-xl font-bold text-primary">MediaSync</h1>
      </div>

      <main className="flex-1 p-8 mt-14 md:mt-0 overflow-y-auto">
        {activeTab === 'dashboard' && (
          <div className="max-w-6xl mx-auto space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-400">Plex Watchlists</p>
                <h2 className="text-3xl font-bold">Dashboard</h2>
              </div>
              <div className="flex gap-3 flex-wrap">
                <button
                  onClick={pullWatchlists}
                  disabled={pulling}
                  className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors ${
                    pulling ? 'bg-gray-700 cursor-not-allowed' : 'bg-gray-900 border border-gray-700 hover:border-primary'
                  }`}
                >
                  <RefreshCw size={18} className={pulling ? 'animate-spin' : ''} />
                  {pulling ? 'Pulling...' : 'Pull from Plex'}
                </button>
                <button
                  onClick={triggerPush}
                  disabled={loading}
                  className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors ${
                    loading ? 'bg-gray-700 cursor-not-allowed' : 'bg-primary hover:bg-primary-hover'
                  }`}
                >
                  <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                  {loading ? 'Pushing...' : 'Push to Radarr/Sonarr'}
                </button>
                <span className="text-sm text-gray-400">Status: {syncStatus}</span>
              </div>
            </div>

            <div className="space-y-6">
              <WatchlistCard title="My Watchlist" items={watchlists.mine} emptyMessage="Nothing here. Enable auto-sync or add items in Plex." onRemove={removeWatchlistItem} />
              <WatchlistCard title="Friend's Watchlist" items={watchlists.friends} emptyMessage="Friend list is clear." onRemove={removeWatchlistItem} />
            </div>

            {gridEmpty && (
              <div className="bg-background border border-dashed border-gray-700 rounded-xl p-6 text-center text-gray-400">
                Watchlists are empty or already synced.
              </div>
            )}
          </div>
        )}

        {activeTab === 'settings' && config && (
          <div className="max-w-5xl mx-auto space-y-6">
            <div className="flex items-center gap-3">
              <Settings className="text-primary" />
              <h2 className="text-3xl font-bold">Settings</h2>
            </div>

            <SettingsPanel
              title="Plex"
              icon={<Shield size={18} />}
              fields={[
                { label: 'Hostname or IP', value: config.plex.url, onChange: (v) => handleInput('plex.url', v) },
                { label: 'Token', value: config.plex.token, onChange: (v) => handleInput('plex.token', v), type: 'password' },
                { label: 'My Watchlist RSS', value: config.plex.rss_my_url, onChange: (v) => handleInput('plex.rss_my_url', v) },
                { label: "Friend's Watchlist RSS", value: config.plex.rss_friend_url, onChange: (v) => handleInput('plex.rss_friend_url', v) },
                { label: 'Auto push interval (seconds)', value: config.plex.auto_sync_interval_seconds, onChange: (v) => handleInput('plex.auto_sync_interval_seconds', Number(v)), type: 'number' },
              ]}
              toggles={[
                { label: 'Enable auto push', value: config.plex.auto_sync_enabled, onChange: (v) => handleInput('plex.auto_sync_enabled', v) },
              ]}
              onTest={() => testService('plex')}
              testing={testing['plex']}
            />

            <SettingsPanel
              title="Radarr"
              icon={<Server size={18} />}
              fields={[
                { label: 'URL', value: config.radarr.url, onChange: (v) => handleInput('radarr.url', v) },
                { label: 'API Key', value: config.radarr.api_key, onChange: (v) => handleInput('radarr.api_key', v), type: 'password' },
                { label: 'Quality Profile ID', value: config.radarr.quality_profile_id, onChange: (v) => handleInput('radarr.quality_profile_id', Number(v)), type: 'number' },
                { label: 'Root Folder', value: config.radarr.root_folder_path, onChange: (v) => handleInput('radarr.root_folder_path', v) },
              ]}
              onTest={() => testService('radarr')}
              testing={testing['radarr']}
            />

            <SettingsPanel
              title="Sonarr"
              icon={<Wifi size={18} />}
              fields={[
                { label: 'URL', value: config.sonarr.url, onChange: (v) => handleInput('sonarr.url', v) },
                { label: 'API Key', value: config.sonarr.api_key, onChange: (v) => handleInput('sonarr.api_key', v), type: 'password' },
                { label: 'Quality Profile ID', value: config.sonarr.quality_profile_id, onChange: (v) => handleInput('sonarr.quality_profile_id', Number(v)), type: 'number' },
                { label: 'Root Folder', value: config.sonarr.root_folder_path, onChange: (v) => handleInput('sonarr.root_folder_path', v) },
              ]}
              onTest={() => testService('sonarr')}
              testing={testing['sonarr']}
            />

            <div className="flex gap-3 justify-end">
              <button
                onClick={saveConfig}
                disabled={saving}
                className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors ${
                  saving ? 'bg-gray-700 cursor-not-allowed' : 'bg-primary hover:bg-primary-hover'
                }`}
              >
                <Save size={18} />
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function SidebarItem({ icon, label, active, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
        active ? 'bg-primary/20 text-primary border-r-2 border-primary' : 'text-gray-400 hover:bg-gray-700 hover:text-white'
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </button>
  );
}

function WatchlistCard({ title, items, emptyMessage, onRemove }: { title: string; items: WatchItem[]; emptyMessage: string; onRemove?: (rating_key: string) => void }) {
  const deriveYear = (item: WatchItem) => {
    if (item.year) return item.year;
    const tokens = (item.title || '').match(/\b(19|20)\d{2}\b/);
    return tokens ? tokens[0] : '';
  };

  return (
    <div className="bg-background rounded-xl border border-gray-800 p-4 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <HardDrive size={16} className="text-primary" />
          <h3 className="text-lg font-semibold">{title}</h3>
        </div>
        <span className="text-sm text-gray-500">{items.length} items</span>
      </div>
      {items.length === 0 ? (
        <div className="text-gray-500 text-sm py-8 text-center">{emptyMessage}</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {items.map((item) => (
            <div key={item.rating_key || item.title} className="bg-surface rounded-xl overflow-hidden border border-gray-800">
              <div className="relative aspect-[2/3]">
                <div
                  className="absolute inset-0 bg-cover bg-center"
                  style={{ backgroundImage: item.poster ? `url(${item.poster})` : 'linear-gradient(135deg, #1f2937, #111827)' }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent opacity-0 hover:opacity-100 transition-opacity">
                  <div className="absolute bottom-0 w-full p-3 space-y-2 text-sm">
                    <p className="font-semibold truncate">{item.title}</p>
                    <p className="text-xs text-gray-300 max-h-14 overflow-hidden text-ellipsis">{item.summary || 'No synopsis available yet.'}</p>
                  </div>
                </div>
                <span className={`absolute top-2 right-2 text-xs px-2 py-1 rounded-full ${statusColor(item.status)}`}>
                  {item.status === 'downloaded' ? 'Downloaded' : item.status === 'added' ? 'Monitored' : 'Not downloaded'}
                </span>
                {item.source && (
                  <span className="absolute bottom-2 right-2 text-[10px] px-2 py-1 rounded-full bg-black/60 text-gray-200">
                    {item.source === 'friends' ? 'Friend' : 'Me'}
                  </span>
                )}
                {onRemove && (
                  <button
                    onClick={() => onRemove(item.rating_key)}
                    className="absolute top-2 left-2 p-2 rounded-full bg-black/60 hover:bg-black/80 transition text-red-300 hover:text-red-100"
                    title="Remove from watchlist"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
              <div className="p-3 space-y-1">
                <p className="font-semibold truncate">{item.title}</p>
                <p className="text-xs text-gray-400">{deriveYear(item) || ' '}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

type Field = { label: string; value: any; onChange: (v: any) => void; type?: string };
type Toggle = { label: string; value: boolean; onChange: (v: boolean) => void };

function SettingsPanel({
  title,
  icon,
  fields,
  toggles,
  onTest,
  testing,
}: {
  title: string;
  icon: JSX.Element;
  fields: Field[];
  toggles?: Toggle[];
  onTest?: () => void;
  testing?: boolean;
}) {
  return (
    <div className="bg-background rounded-xl border border-gray-800 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon}
          <h3 className="text-xl font-semibold">{title}</h3>
        </div>
        {onTest && (
          <button
            onClick={onTest}
            disabled={testing}
            className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm ${
              testing ? 'bg-gray-700 cursor-not-allowed' : 'bg-gray-900 border border-gray-700 hover:border-primary'
            }`}
          >
            <TestTube2 size={14} />
            {testing ? 'Testing...' : 'Test'}
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {fields.map((f) => (
          <div key={f.label} className="flex flex-col gap-2">
            <label className="text-sm text-gray-400">{f.label}</label>
            <input
              type={f.type || 'text'}
              value={f.value ?? ''}
              onChange={(e) => f.onChange(f.type === 'number' ? Number(e.target.value) : e.target.value)}
              className="bg-surface border border-gray-800 rounded-md px-3 py-2 text-sm focus:border-primary focus:outline-none"
            />
          </div>
        ))}
      </div>
      {toggles && toggles.length > 0 && (
        <div className="flex flex-wrap gap-4">
          {toggles.map((t) => (
            <label key={t.label} className="inline-flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={t.value}
                onChange={(e) => t.onChange(e.target.checked)}
                className="form-checkbox h-4 w-4 text-primary"
              />
              {t.label}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
