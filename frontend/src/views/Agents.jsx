import React, { useState, useEffect } from 'react';
import { 
  Users, Zap, Bell, Trash2, Globe, Search, MoreVertical, 
  Shield, AlertCircle, Activity, BarChart3, Clock, 
  ChevronRight, ExternalLink, Power, LayoutGrid, List, RefreshCw,
  Sliders, Terminal
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const Agents = ({ 
  onCreateAgent, 
  notificationsEnabled, 
  setNotificationsEnabled,
  agents,
  setAgents,
  loading,
  fetchAgents
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [celeryStatus, setCeleryStatus] = useState('up');

  const checkHealth = async () => {
    const requestController = new AbortController();
    const timeoutId = setTimeout(() => requestController.abort(), 3000);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/health`, {
        signal: requestController.signal
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        setCeleryStatus(data.services?.celery || 'up');
      }
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') return;
      console.warn("Health check failed:", err);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchAgents(true);
    await checkHealth();
    setIsRefreshing(false);
  };

  useEffect(() => {
    checkHealth();
    
    // Refresh health status every 30 seconds
    const interval = setInterval(() => {
      checkHealth();
    }, 30000);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, []);

  const deleteAgent = async (id) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/agents/${id}`, { 
        method: 'DELETE',
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (res.ok) {
        setAgents(prev => prev.filter(a => a.id !== id));
      } else {
        const errorData = await res.json();
        alert(`Failed to delete agent: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (err) {
      clearTimeout(timeoutId);
      console.error('Delete failed:', err);
      alert('Network error while deleting agent.');
    }
  };

  const toggleAlerts = async (agent) => {
    const originalStatus = agent.enable_alerts;
    const newStatus = originalStatus ? 0 : 1;
    
    // Optimistic UI update
    setAgents(prev => prev.map(a => a.id === agent.id ? { ...a, enable_alerts: newStatus } : a));
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/agents/${agent.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable_alerts: newStatus }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (!res.ok) {
        throw new Error('Server update failed');
      }
    } catch (err) {
      clearTimeout(timeoutId);
      console.error('Toggle alerts failed:', err);
      // Revert UI state on failure
      setAgents(prev => prev.map(a => a.id === agent.id ? { ...a, enable_alerts: originalStatus } : a));
      alert('Failed to update alert settings. Please try again.');
    }
  };

  const [activeMenu, setActiveMenu] = useState(null);
  const [agentToDelete, setAgentToDelete] = useState(null);

  const toggleGlobalNotifications = () => {
    setNotificationsEnabled(!notificationsEnabled);
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1 }
  };

  return (
    <div 
      className="flex-1 min-h-full bg-gray-50/50"
      onClick={() => setActiveMenu(null)}
    >
      <div className="max-w-7xl mx-auto p-6 md:p-10 space-y-10">
        {/* Celery Down Warning */}
        <AnimatePresence>
          {celeryStatus === 'down' && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="flex items-center gap-4 p-5 bg-amber-50 border border-amber-200 rounded-3xl text-amber-800"
            >
              <div className="p-3 bg-amber-100 rounded-2xl">
                <AlertCircle size={24} />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-black uppercase tracking-widest">Worker Engine Offline</p>
                <p className="text-xs font-bold text-amber-700/80 uppercase tracking-tight">
                  Background discovery and automated tasks are temporarily paused.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Professional Header Section */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 bg-white p-8 rounded-[2.5rem] border border-gray-100 shadow-sm">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 rounded-full border border-blue-100">
              <Activity size={14} className="text-blue-600" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-blue-600">Agent Command Center</span>
            </div>
            <div className="space-y-2">
              <h1 className="text-4xl font-black text-gray-900 tracking-tight italic uppercase">
                My Agents
              </h1>
              <p className="text-black text-sm font-medium max-w-xl">
                Manage your autonomous discovery agents and monitoring nodes.
              </p>
            </div>
          </div>
          
          <div className="flex flex-wrap items-center gap-4">
            <button 
              onClick={(e) => {
                e.stopPropagation();
                onCreateAgent();
              }}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-2xl font-bold uppercase tracking-widest text-xs shadow-lg shadow-blue-200 transition-all active:scale-95 flex items-center gap-3 group"
            >
              <Zap size={18} className="group-hover:animate-pulse" />
              Create Agent
            </button>

            <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 rounded-xl border border-gray-100">
              <span className="text-[10px] font-bold text-black uppercase tracking-widest">Notifications</span>
              <button
                onClick={toggleGlobalNotifications}
                className={`w-10 h-5 rounded-full relative transition-colors duration-300 ${notificationsEnabled ? 'bg-green-500' : 'bg-gray-300'}`}
              >
                <motion.div 
                  animate={{ x: notificationsEnabled ? 22 : 2 }}
                  className="absolute top-1 w-3 h-3 rounded-full bg-white shadow-sm" 
                />
              </button>
            </div>

            <div className="flex bg-gray-50 border border-gray-100 rounded-xl p-1 shadow-sm">
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  handleRefresh();
                }}
                className="p-2 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-white transition-all"
                title="Refresh Status"
              >
                <RefreshCw size={18} className={isRefreshing ? 'animate-spin' : ''} />
              </button>
              <div className="w-px h-4 bg-gray-200 self-center mx-1" />
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  setViewMode('grid');
                }}
                className={`p-2 rounded-lg transition-all ${viewMode === 'grid' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-400 hover:text-gray-900'}`}
              >
                <LayoutGrid size={18} />
              </button>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  setViewMode('list');
                }}
                className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-400 hover:text-gray-900'}`}
              >
                <List size={18} />
              </button>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="h-64 bg-white rounded-[2rem] animate-pulse border border-gray-100 shadow-sm" />
            ))}
          </div>
        ) : agents.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex flex-col items-center justify-center py-32 bg-white rounded-[3rem] border border-dashed border-gray-200 shadow-inner"
          >
            <div className="w-24 h-24 bg-gray-50 rounded-[2rem] flex items-center justify-center mb-8 text-gray-400 shadow-xl">
              <Users size={48} />
            </div>
            <h3 className="text-2xl font-black text-gray-900 uppercase tracking-tight italic">No Discovery Nodes</h3>
            <p className="text-black text-sm font-medium mb-10 max-w-sm text-center">
              Your fleet is currently offline. Deploy your first autonomous agent to begin real-time lead discovery.
            </p>
            <button 
              onClick={(e) => {
                e.stopPropagation();
                onCreateAgent();
              }}
              className="bg-blue-600 hover:bg-blue-700 text-white px-10 py-5 rounded-2xl font-black uppercase tracking-widest text-xs shadow-xl shadow-blue-200 transition-all active:scale-95 flex items-center gap-3"
            >
              <Zap size={18} />
              Initiate Deployment
            </button>
          </motion.div>
        ) : (
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className={viewMode === 'grid' 
              ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
              : "space-y-4"
            }
          >
            <AnimatePresence mode='popLayout'>
              {agents.map((agent) => (
                <AgentCard 
                  key={agent.id} 
                  agent={agent} 
                  viewMode={viewMode}
                  onDelete={() => setAgentToDelete(agent)}
                  onToggleAlerts={toggleAlerts}
                  variants={itemVariants}
                  activeMenu={activeMenu}
                  setActiveMenu={setActiveMenu}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        )}

        {/* Delete Confirmation Modal */}
        <AnimatePresence>
          {agentToDelete && (
            <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-gray-100"
              >
                <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center text-red-500 mb-6">
                  <Trash2 size={32} />
                </div>
                <h3 className="text-2xl font-black text-gray-900 uppercase italic mb-2">Terminate Agent?</h3>
                <p className="text-gray-500 text-sm font-medium mb-8">
                  Are you sure you want to terminate <span className="text-gray-900 font-bold">{agentToDelete.name}</span>? This action cannot be undone and all active discovery will cease.
                </p>
                <div className="flex gap-4">
                  <button 
                    onClick={() => setAgentToDelete(null)}
                    className="flex-1 px-6 py-4 rounded-xl font-bold text-gray-500 hover:bg-gray-50 transition-all"
                  >
                    Cancel
                  </button>
                  <button 
                    onClick={() => {
                      deleteAgent(agentToDelete.id);
                      setAgentToDelete(null);
                    }}
                    className="flex-1 px-6 py-4 bg-red-600 hover:bg-red-700 text-white rounded-xl font-bold transition-all shadow-lg shadow-red-100"
                  >
                    Terminate
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        {/* Fleet Security Banner */}
        <div className="bg-slate-950 rounded-[2.5rem] p-8 md:p-12 relative overflow-hidden group border border-slate-800 shadow-2xl">
          <div className="absolute inset-0 opacity-10 pointer-events-none" 
               style={{ backgroundImage: 'radial-gradient(#3B82F6 0.5px, transparent 0.5px)', backgroundSize: '24px 24px' }} />
          
          <div className="relative z-10 flex flex-col md:flex-row items-center gap-10">
            <div className="w-20 h-20 bg-blue-600/10 rounded-[1.5rem] flex items-center justify-center text-blue-500 border border-blue-500/20 shadow-inner group-hover:scale-110 transition-transform">
              <Shield size={40} />
            </div>
            <div className="flex-1 space-y-3 text-center md:text-left">
              <h3 className="text-xl font-black text-white uppercase tracking-tight italic">Fleet Integrity Protocol</h3>
              <p className="text-slate-400 text-sm font-medium max-w-2xl leading-relaxed">
                All autonomous discovery agents are operating under military-grade encryption and rate-limiting protocols to ensure maximum stealth and platform longevity.
              </p>
            </div>
            <div className="flex items-center gap-3 px-6 py-3 bg-slate-900 rounded-2xl border border-slate-800">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">All Systems Nominal</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const AgentCard = React.forwardRef(({ agent, viewMode, onDelete, onToggleAlerts, variants, activeMenu, setActiveMenu }, ref) => {
  const isMenuOpen = activeMenu === agent.id;

  if (viewMode === 'list') {
    return (
      <motion.div 
        ref={ref}
        variants={variants}
        layout
        className="group bg-white border border-gray-100 rounded-2xl p-4 flex items-center justify-between hover:border-blue-200 hover:shadow-lg transition-all duration-300 relative"
      >
        <div className="flex items-center gap-6 flex-1">
          <div className="w-12 h-12 bg-gray-50 rounded-xl flex items-center justify-center text-blue-600 group-hover:bg-blue-50 group-hover:scale-110 transition-all duration-300 font-bold">
            {agent.name[0].toUpperCase()}
          </div>
          <div className="flex flex-col min-w-[200px]">
            <h3 className="text-gray-900 font-black text-base uppercase tracking-tight leading-none italic group-hover:text-blue-600 transition-colors">{agent.name}</h3>
            <span className="text-[10px] font-bold text-black uppercase tracking-widest mt-1 italic truncate max-w-[300px]">Query: {agent.query}</span>
          </div>
          <div className="hidden lg:flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-xl border border-gray-100 group-hover:border-blue-100 transition-colors">
            <Globe size={12} className="text-blue-600" />
            <span className="text-[10px] font-bold text-black uppercase tracking-widest">{agent.location}</span>
          </div>
          <div className="hidden xl:flex items-center gap-4">
            <div className="flex flex-col items-center group/stat">
              <span className="text-[8px] font-bold text-black uppercase tracking-widest group-hover/stat:text-blue-600 transition-colors">Signals</span>
              <span className="text-sm font-black text-gray-900 italic">{agent.signals_count || 0}</span>
            </div>
            <div className="flex flex-col items-center group/stat">
              <span className="text-[8px] font-bold text-black uppercase tracking-widest group-hover/stat:text-blue-600 transition-colors">Status</span>
              <div className="flex items-center gap-1">
                <div className="w-1 h-1 bg-green-500 rounded-full animate-pulse" />
                <span className="text-[10px] font-bold text-green-600 uppercase tracking-widest">Active</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => onToggleAlerts(agent)}
            className={`p-2.5 rounded-xl border transition-all duration-300 ${
              agent.enable_alerts 
                ? 'bg-blue-50 border-blue-100 text-blue-600 shadow-sm hover:bg-blue-100' 
                : 'bg-gray-50 border-gray-100 text-gray-400 hover:border-gray-200 hover:bg-gray-100'
            }`}
            title={agent.enable_alerts ? 'Mute Alerts' : 'Enable Alerts'}
          >
            <Bell size={18} className={agent.enable_alerts ? 'animate-bounce' : ''} />
          </button>
          
          <div className="relative">
            <button 
              onClick={(e) => {
                e.stopPropagation();
                setActiveMenu(isMenuOpen ? null : agent.id);
              }}
              className={`p-2.5 text-gray-400 hover:text-gray-900 hover:bg-gray-50 rounded-xl transition-all duration-300 border border-transparent ${isMenuOpen ? 'bg-gray-50 border-gray-200 text-gray-900 shadow-inner' : ''}`}
            >
              <MoreVertical size={18} />
            </button>

            <AnimatePresence>
              {isMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: 10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: 10 }}
                  className="absolute right-0 mt-2 w-48 bg-white border border-gray-100 rounded-xl shadow-2xl z-20 overflow-hidden"
                >
                  <div className="p-1">
                    <button className="w-full text-left px-3 py-2 text-xs font-bold text-gray-600 hover:bg-gray-50 hover:text-blue-600 rounded-lg transition-all flex items-center gap-2 group/item">
                      <Sliders size={14} className="group-hover/item:rotate-12 transition-transform" />
                      Parameters
                    </button>
                    <button 
                      onClick={() => onDelete(agent.id)}
                      className="w-full text-left px-3 py-2 text-xs font-bold text-red-500 hover:bg-red-50 rounded-lg transition-all flex items-center gap-2 group/item"
                    >
                      <Trash2 size={14} className="group-hover/item:scale-110 transition-transform" />
                      Terminate
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div 
      ref={ref}
      variants={variants}
      layout
      className="group bg-white border border-gray-100 rounded-[2.5rem] p-8 shadow-sm hover:shadow-2xl hover:border-blue-200 transition-all duration-500 flex flex-col gap-8 relative overflow-hidden"
    >
      {/* Decorative Background Icon */}
      <div className="absolute -bottom-6 -right-6 opacity-[0.03] text-blue-600 pointer-events-none group-hover:scale-110 group-hover:opacity-[0.06] transition-all duration-700">
        <Shield size={180} />
      </div>

      {/* Card Header */}
      <div className="flex justify-between items-start relative z-10">
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 bg-blue-50 rounded-[1.5rem] flex items-center justify-center text-blue-600 group-hover:scale-110 group-hover:shadow-xl group-hover:shadow-blue-100 transition-all duration-500 shadow-inner font-black text-2xl italic">
            {agent.name[0].toUpperCase()}
          </div>
          <div className="space-y-1">
            <h3 className="text-xl font-black text-gray-900 tracking-tighter italic uppercase leading-tight group-hover:text-blue-600 transition-colors">{agent.name}</h3>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-2 py-0.5 bg-green-50 rounded-lg border border-green-100">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                <span className="text-[9px] font-bold text-green-600 uppercase tracking-widest">Active</span>
              </div>
              <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest">Patrolling {agent.location} ({agent.radius}km)</span>
            </div>
            <div className="text-[9px] font-black text-blue-600/60 uppercase tracking-widest mt-1">
              Min Confidence: {agent.min_intent_score * 100}%
            </div>
          </div>
        </div>
        
        <div className="relative">
          <button 
            onClick={(e) => {
              e.stopPropagation();
              setActiveMenu(isMenuOpen ? null : agent.id);
            }}
            className={`p-2 text-gray-400 hover:text-gray-900 hover:bg-gray-50 rounded-xl transition-all duration-300 border border-transparent hover:border-gray-100 ${isMenuOpen ? 'bg-gray-50 border-gray-200 text-gray-900 shadow-inner' : ''}`}
          >
            <MoreVertical size={20} />
          </button>

          <AnimatePresence>
            {isMenuOpen && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 10 }}
                className="absolute right-0 mt-2 w-52 bg-white border border-gray-100 rounded-xl shadow-2xl z-20 overflow-hidden"
              >
                <div className="p-1.5">
                  <button className="w-full text-left px-3 py-2.5 text-xs font-bold text-gray-600 hover:bg-gray-50 hover:text-blue-600 rounded-lg transition-all flex items-center gap-2 group/item">
                    <Sliders size={14} className="group-hover/item:rotate-12 transition-transform" />
                    Edit Parameters
                  </button>
                  <button 
                    onClick={() => onDelete(agent.id)}
                    className="w-full text-left px-3 py-2.5 text-xs font-bold text-red-500 hover:bg-red-50 rounded-lg transition-all flex items-center gap-2 group/item"
                  >
                    <Trash2 size={14} className="group-hover/item:scale-110 transition-transform" />
                    Terminate Agent
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Metrics Section */}
      <div className="grid grid-cols-2 gap-4 relative z-10">
        <div className="bg-gray-50 p-4 rounded-2xl border border-gray-100 flex flex-col gap-1 group/stat hover:border-blue-100 transition-colors">
          <span className="text-[9px] font-bold text-black uppercase tracking-widest flex items-center gap-1.5 group-hover/stat:text-blue-600 transition-colors">
            <BarChart3 size={10} />
            Signals Found
          </span>
          <span className="text-lg font-black text-gray-900 italic group-hover/stat:text-blue-600 transition-colors">{agent.signals_count || 0}</span>
        </div>
        <div className="bg-gray-50 p-4 rounded-2xl border border-gray-100 flex flex-col gap-1 group/stat hover:border-blue-100 transition-colors">
          <span className="text-[9px] font-bold text-black uppercase tracking-widest flex items-center gap-1.5 group-hover/stat:text-blue-600 transition-colors">
            <Clock size={10} />
            Uptime
          </span>
          <span className="text-lg font-black text-gray-900 italic group-hover/stat:text-blue-600 transition-colors">
            {(() => {
              if (!agent.created_at) return '0h';
              const created = new Date(agent.created_at);
              const now = new Date();
              const diffMs = now - created;
              const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
              if (diffHours < 24) return `${diffHours}h`;
              const diffDays = Math.floor(diffHours / 24);
              return `${diffDays}d ${diffHours % 24}h`;
            })()}
          </span>
        </div>
      </div>

      {/* Contact/Query Section */}
      <div className="space-y-4 relative z-10">
        <div className="flex flex-col gap-2">
          <span className="text-[9px] font-bold text-black uppercase tracking-widest">Active Discovery Query</span>
          <div className="bg-gray-900 text-gray-100 px-4 py-3 rounded-xl font-mono text-[10px] flex items-center justify-between group/code">
            <span className="truncate mr-2">"{agent.query}"</span>
            <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
          </div>
        </div>

        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => onToggleAlerts(agent)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all text-[10px] font-bold uppercase tracking-widest ${
                agent.enable_alerts 
                  ? 'bg-blue-50 border-blue-100 text-blue-600' 
                  : 'bg-gray-50 border-gray-100 text-gray-400'
              }`}
            >
              <Bell size={12} className={agent.enable_alerts ? 'animate-bounce' : ''} />
              {agent.enable_alerts ? 'Alerts On' : 'Alerts Off'}
            </button>
          </div>
          <button className="flex items-center gap-1.5 text-[10px] font-bold text-blue-600 uppercase tracking-widest hover:translate-x-1 transition-transform">
            View Reports
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </motion.div>
  );
});

AgentCard.displayName = 'AgentCard';

export default Agents;
