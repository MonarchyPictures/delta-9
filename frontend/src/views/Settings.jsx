import React, { useState, useEffect } from 'react';
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import getApiUrl, { getApiKey } from '../config';

const Settings = ({ notificationsEnabled, setNotificationsEnabled, soundEnabled, setSoundEnabled }) => {
  const [scrapers, setScrapers] = useState({});
  const [loadingScrapers, setLoadingScrapers] = useState(true);

  const fetchScrapers = async () => {
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      const res = await fetch(`${apiUrl}/scrapers/status`, {
        headers: {
          'X-API-Key': apiKey,
          'x-admin': 'true'
        }
      });
      if (res.ok) {
        const data = await res.json();
        setScrapers(data);
      }
    } catch (err) {
      console.error("Failed to fetch scrapers:", err);
    } finally {
      setLoadingScrapers(false);
    }
  };

  useEffect(() => {
    fetchScrapers();
  }, []);

  const toggleScraper = async (name, currentStatus) => {
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      const endpoint = currentStatus ? 'disable' : 'enable';
      const res = await fetch(`${apiUrl}/scrapers/${name}/${endpoint}`, {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey,
          'x-admin': 'true'
        }
      });
      if (res.ok) {
        fetchScrapers();
      }
    } catch (err) {
      console.error(`Failed to ${currentStatus ? 'disable' : 'enable'} scraper:`, err);
    }
  };

  const toggleMode = async (name, currentMode) => {
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      const newMode = currentMode === 'production' ? 'sandbox' : 'production';
      const res = await fetch(`${apiUrl}/scrapers/${name}/mode?mode=${newMode}`, {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey,
          'x-admin': 'true'
        }
      });
      if (res.ok) {
        fetchScrapers();
      }
    } catch (err) {
      console.error("Failed to toggle mode:", err);
    }
  };

  const promoteScraper = async (name) => {
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      const res = await fetch(`${apiUrl}/scrapers/${name}/promote`, {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey,
          'x-admin': 'true'
        }
      });
      if (res.ok) {
        fetchScrapers();
      }
    } catch (err) {
      console.error("Failed to promote scraper:", err);
    }
  };

  const formatTTL = (seconds) => {
    if (!seconds) return null;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const calculateSuccessRate = (metrics) => {
    if (!metrics || !metrics.runs) return '0%';
    const rate = (metrics.verified / metrics.runs) * 100;
    return `${rate.toFixed(1)}%`;
  };

  const updateSettings = async (newSettings) => {
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      await fetch(`${apiUrl}/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify(newSettings)
      });
    } catch (err) {
      console.error("Failed to update settings:", err);
    }
  };

  const toggleNotifications = () => {
    const newValue = !notificationsEnabled;
    setNotificationsEnabled(newValue);
    updateSettings({ notifications_enabled: newValue });
  };

  const toggleSound = () => {
    const newValue = !soundEnabled;
    setSoundEnabled(newValue);
    updateSettings({ sound_enabled: newValue });
  };

  return (
    <div className="flex-1 bg-black p-8 text-white overflow-y-auto">
      <div className="max-w-2xl mx-auto space-y-12">
        <h1 className="text-4xl font-black italic tracking-tighter">SETTINGS</h1>
        
        <div className="space-y-6">
          <div className="bg-white/5 border border-white/10 rounded-3xl p-6 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-lg">Push Notifications</h3>
              <p className="text-white/40 text-sm italic">Alert me when new leads appear in Nairobi</p>
            </div>
            <button 
              onClick={toggleNotifications}
              className={`w-14 h-8 rounded-full transition-all ${notificationsEnabled ? 'bg-blue-600' : 'bg-white/10'}`}
            >
              <div className={`w-6 h-6 bg-white rounded-full transition-all transform ${notificationsEnabled ? 'translate-x-7' : 'translate-x-1'}`} />
            </button>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-3xl p-6 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-lg">Alert Sound</h3>
              <p className="text-white/40 text-sm italic">Play a sound for high-confidence intents</p>
            </div>
            <button 
              onClick={toggleSound}
              className={`w-14 h-8 rounded-full transition-all ${soundEnabled ? 'bg-blue-600' : 'bg-white/10'}`}
            >
              <div className={`w-6 h-6 bg-white rounded-full transition-all transform ${soundEnabled ? 'translate-x-7' : 'translate-x-1'}`} />
            </button>
          </div>
        </div>

        <div className="space-y-6 pt-12 border-t border-white/10">
          <h2 className="text-2xl font-black italic tracking-tight">SCRAPER CONTROL</h2>
          
          {loadingScrapers ? (
            <div className="text-white/20 italic animate-pulse">Loading scraper status...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(scrapers).map(([name, data]) => (
                <div key={name} className="bg-white/5 border border-white/10 rounded-3xl p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-bold text-lg">{name}</h3>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {data.core && (
                          <span className="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">CORE</span>
                        )}
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${data.enabled ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                          {data.enabled ? 'ON' : 'OFF'}
                        </span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${data.mode === 'sandbox' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-purple-500/20 text-purple-400'}`}>
                          {data.mode?.toUpperCase() || 'PRODUCTION'}
                        </span>
                        {data.ttl_remaining > 0 && (
                          <span className="text-[10px] bg-orange-500/20 text-orange-400 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider animate-pulse">
                            TTL: {formatTTL(data.ttl_remaining)}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {data.mode === 'sandbox' && (
                        <button 
                          onClick={() => promoteScraper(name)}
                          className="text-[10px] bg-white/10 hover:bg-white/20 text-white px-3 py-1.5 rounded-full font-black italic transition-all uppercase tracking-tighter border border-white/10"
                        >
                          PROMOTE
                        </button>
                      )}
                      <button 
                        onClick={() => toggleScraper(name, data.enabled)}
                        className={`w-12 h-6 rounded-full transition-all ${data.enabled ? 'bg-blue-600' : 'bg-white/10'}`}
                      >
                        <div className={`w-4 h-4 bg-white rounded-full transition-all transform ${data.enabled ? 'translate-x-7' : 'translate-x-1'}`} />
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-4 gap-2 pt-2">
                    <div className="text-center p-2 bg-black/20 rounded-xl">
                      <div className="text-xs text-white/40 italic">Runs</div>
                      <div className="font-bold text-sm">{data.metrics?.runs || 0}</div>
                    </div>
                    <div className="text-center p-2 bg-black/20 rounded-xl">
                      <div className="text-xs text-white/40 italic">Verified</div>
                      <div className="font-bold text-sm text-green-400">{data.metrics?.verified || 0}</div>
                    </div>
                    <div className="text-center p-2 bg-black/20 rounded-xl">
                      <div className="text-xs text-white/40 italic">Success</div>
                      <div className="font-bold text-sm text-blue-400">{calculateSuccessRate(data.metrics)}</div>
                    </div>
                    <div className="text-center p-2 bg-black/20 rounded-xl">
                      <div className="text-xs text-white/40 italic">Failures</div>
                      <div className="font-bold text-sm text-red-400/60">{data.metrics?.failures || 0}</div>
                    </div>
                  </div>

                  {/* Scraper Health Chart */}
                  {data.metrics?.history && data.metrics.history.length > 0 && (
                    <div className="h-24 w-full mt-4 bg-black/20 rounded-2xl p-2 overflow-hidden">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data.metrics.history}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#111', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', fontSize: '10px' }}
                            itemStyle={{ padding: '0px' }}
                          />
                          <Line 
                            type="monotone" 
                            dataKey="verified" 
                            stroke="#4ade80" 
                            strokeWidth={2} 
                            dot={false} 
                            isAnimationActive={false}
                          />
                          <Line 
                            type="monotone" 
                            dataKey="leads" 
                            stroke="#3b82f6" 
                            strokeWidth={1} 
                            strokeDasharray="3 3"
                            dot={false} 
                            isAnimationActive={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                  
                  {(!data.metrics?.history || data.metrics.history.length === 0) && (
                    <div className="h-24 w-full mt-4 bg-white/5 rounded-2xl flex items-center justify-center">
                      <span className="text-[10px] text-white/10 uppercase tracking-widest font-black">No History Data</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="pt-12 border-t border-white/10">
          <p className="text-[10px] font-black uppercase tracking-[0.4em] text-white/20">Production Version 1.0.0 // Delta9</p>
        </div>
      </div>
    </div>
  );
};

export default Settings;