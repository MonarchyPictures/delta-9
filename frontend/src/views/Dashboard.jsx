import React, { useState, useEffect } from 'react';
import { 
  Activity, Users, Target, Zap, TrendingUp, ShieldCheck, 
  ArrowUpRight, Clock, MessageSquare, Search, Globe, AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import SummaryCards from '../components/SummaryCards';
import { Link } from 'react-router-dom';

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalLeads: '0',
    activeAgents: '0',
    todayActivity: '0',
  });
  const [recentLeads, setRecentLeads] = useState([]);
  const [agents, setAgents] = useState([]);
  const [health, setHealth] = useState({
    status: 'healthy',
    services: { database: 'up', celery: 'up' }
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    let isMounted = true;
    let interval;

    const fetchDashboardData = async (isPolling = false) => {
      try {
        if (!isPolling) setLoading(true);
        
        const fetchWithTimeout = async (url, timeout = 15000) => {
          const requestController = new AbortController();
          const timeoutId = setTimeout(() => requestController.abort(), timeout);
          
          try {
            const res = await fetch(url, { 
              signal: requestController.signal 
            });
            clearTimeout(timeoutId);
            if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
            return res.json();
          } catch (err) {
            clearTimeout(timeoutId);
            if (err.name === 'AbortError' || err.message?.includes('aborted')) {
              // Return a "cancelled" marker that Promise.allSettled will catch as fulfilled or we can filter
              throw { name: 'AbortError', message: 'Request was aborted' };
            }
            throw err;
          }
        };

        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const fetchStats = () => fetchWithTimeout(`${apiUrl}/stats`);
        const fetchLeads = () => fetchWithTimeout(`${apiUrl}/leads/search?limit=5`);
        const fetchAgents = () => fetchWithTimeout(`${apiUrl}/agents`);
        const fetchHealthCheck = () => fetchWithTimeout(`${apiUrl}/health`);

        // Fetch everything in parallel but handle individual failures
        const [statsResult, leadsResult, agentsResult, healthResult] = await Promise.allSettled([
          fetchStats(),
          fetchLeads(),
          fetchAgents(),
          fetchHealthCheck()
        ]);

        if (!isMounted) return;

        // Reset error state if we get some data
        setError(null);

        if (statsResult.status === 'fulfilled') {
          setStats(statsResult.value);
          if (statsResult.value.status === 'partial') {
            console.warn("Dashboard stats partial:", statsResult.value.message);
          }
        }
        
        if (leadsResult.status === 'fulfilled') {
          setRecentLeads(leadsResult.value.results || []);
        }
        
        if (agentsResult.status === 'fulfilled') {
          setAgents(Array.isArray(agentsResult.value) ? agentsResult.value.slice(0, 2) : []);
        }
        
        if (healthResult.status === 'fulfilled') {
          setHealth(healthResult.value);
          if (healthResult.value.services?.celery === "down") {
            setError({
              type: 'warning',
              message: 'Background discovery is temporarily unavailable. Some features may be delayed.'
            });
          } else if (healthResult.value.status === 'degraded') {
            setError({
              type: 'warning',
              message: 'System is running in degraded mode. Performance may be impacted.'
            });
          }
        } else {
          // Health check failed implies connectivity issue
          console.error("Health check failed:", healthResult.reason);
          setError({
            type: 'error',
            message: 'Unable to connect to intelligence server. System offline.'
          });
        }
      } catch (err) {
        if (!isMounted) return;
        if (err.name === 'AbortError' || err.message?.includes('aborted')) return;
        console.error("Dashboard fetch error:", err);
        setError({
          type: 'error',
          message: 'Failed to synchronize dashboard data.'
        });
      } finally {
        if (isMounted && !isPolling) setLoading(false);
      }
    };

    fetchDashboardData();
    interval = setInterval(() => fetchDashboardData(true), 30000);

    return () => {
      isMounted = false;
      controller.abort();
      if (interval) clearInterval(interval);
    };
  }, []);

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  };

  return (
    <div className="flex-1 overflow-y-auto no-scrollbar py-8 space-y-10 px-4 md:px-8">
      {/* Resilience Warning Banner */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${
              error.type === 'error' 
                ? 'bg-red-50 border-red-100 text-red-700' 
                : 'bg-amber-50 border-amber-100 text-amber-700'
            }`}
          >
            <AlertCircle size={18} className="shrink-0" />
            <p className="text-xs font-bold uppercase tracking-wider">{error.message}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Welcome Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1">
          <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase italic">
            Command <span className="text-blue-600">Center</span>
          </h1>
          <p className="text-xs font-bold text-gray-400 uppercase tracking-[0.3em]">
            Aggressive Market Intelligence Overview
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Link 
            to="/radar"
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-xl font-black uppercase tracking-widest text-[10px] shadow-lg shadow-blue-600/20 hover:bg-blue-700 transition-all active:scale-95"
          >
            <Search size={16} />
            Launch Discovery
          </Link>
          <div className="flex items-center gap-2 px-4 py-3 bg-green-50 text-green-600 border border-green-100 rounded-xl font-black uppercase tracking-widest text-[10px]">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            System Live
          </div>
        </div>
      </div>

      {/* Recent High-Intent Signals - Primary Focus */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent High-Intent Signals */}
        <motion.div 
          variants={container}
          initial="hidden"
          animate="show"
          className="lg:col-span-2 space-y-6"
        >
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-black text-gray-900 tracking-tight uppercase italic flex items-center gap-3">
              <Zap size={20} className="text-amber-500 fill-amber-500" />
              High-Intent Signals
            </h2>
            <Link to="/leads" className="text-[10px] font-black text-blue-600 uppercase tracking-widest hover:underline flex items-center gap-1">
              View All <ArrowUpRight size={14} />
            </Link>
          </div>

          <div className="space-y-4">
            {loading ? (
              [1, 2, 3].map(i => (
                <div key={i} className="h-24 bg-gray-100 rounded-2xl animate-pulse" />
              ))
            ) : recentLeads.length > 0 ? (
              recentLeads.map((lead) => (
                <motion.div 
                  key={lead.id}
                  variants={item}
                  className="group bg-white border border-gray-100 p-5 rounded-2xl shadow-sm hover:shadow-md transition-all flex items-start gap-4 cursor-pointer"
                  onClick={() => window.open(lead.post_link, '_blank')}
                >
                  <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600 shrink-0 group-hover:scale-110 transition-transform">
                    <Target size={24} />
                  </div>
                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">{lead.source_platform}</span>
                      <span className="text-[10px] font-bold text-green-600 bg-green-50 px-2 py-0.5 rounded-md">{(lead.deal_probability || lead.intent_score * 100).toFixed(0)}% Match</span>
                    </div>
                    <p className="text-sm font-bold text-gray-900 line-clamp-1 italic">"{lead.buyer_request_snippet}"</p>
                    <div className="flex items-center gap-3 pt-1">
                      <div className="flex items-center gap-1 text-[10px] font-bold text-gray-400">
                        <Globe size={12} />
                        {lead.location_raw}
                      </div>
                      <div className="flex items-center gap-1 text-[10px] font-bold text-gray-400">
                        <Clock size={12} />
                        {lead.created_at ? new Date(lead.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'Just now'}
                      </div>
                    </div>
                  </div>
                  <div className="self-center p-2 text-gray-300 group-hover:text-blue-600 transition-colors">
                    <ArrowUpRight size={20} />
                  </div>
                </motion.div>
              ))
            ) : (
              <div className="bg-gray-50 border-2 border-dashed border-gray-200 rounded-2xl py-12 text-center space-y-2">
                <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">No signals captured yet</p>
                <Link to="/radar" className="text-blue-600 text-xs font-bold hover:underline">Launch discovery radar to find leads</Link>
              </div>
            )}
          </div>
        </motion.div>

        {/* Sidebar Intelligence */}
        <div className="space-y-8">
          {/* Active Agents */}
          <div className="bg-gray-900 rounded-3xl p-6 text-white space-y-6 shadow-2xl relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-600/20 blur-3xl -translate-y-1/2 translate-x-1/2 group-hover:bg-blue-600/30 transition-colors" />
            
            <div className="space-y-1 relative">
              <h3 className="text-lg font-black uppercase italic tracking-tight flex items-center gap-2">
                <Users size={20} className="text-blue-400" />
                Active Agents
              </h3>
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Autonomous Hunter Fleet</p>
            </div>

            <div className="space-y-3 relative">
              {agents.length > 0 ? (
                agents.map(agent => (
                  <div key={agent.id} className="flex items-center justify-between p-3 bg-white/5 rounded-xl border border-white/10">
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 ${agent.is_active ? 'bg-green-500 animate-pulse' : 'bg-gray-500'} rounded-full`} />
                      <span className="text-xs font-bold uppercase tracking-wider">{agent.name}</span>
                    </div>
                    <span className="text-[10px] font-black text-blue-400 uppercase">{agent.is_active ? 'Patrolling' : 'Idle'}</span>
                  </div>
                ))
              ) : (
                <p className="text-[10px] font-bold text-gray-500 text-center py-4 uppercase tracking-widest">No agents deployed</p>
              )}
            </div>

            <Link to="/agents" className="block w-full py-3 bg-white text-gray-900 rounded-xl text-center font-black uppercase tracking-widest text-[10px] hover:bg-gray-100 transition-colors">
              Manage Fleet
            </Link>
          </div>

          {/* System Health */}
          <div className="bg-white border border-gray-100 rounded-3xl p-6 space-y-6 shadow-sm">
            <div className="space-y-1">
              <h3 className="text-lg font-black uppercase italic tracking-tight flex items-center gap-2">
                <Activity size={20} className="text-green-500" />
                Network Status
              </h3>
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Real-time Node Monitoring</p>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Database Node</span>
                <span className={`text-[10px] font-black ${health.services?.database === 'up' ? 'text-green-600' : 'text-red-600'} uppercase`}>
                  {health.services?.database === 'up' ? 'ONLINE' : 'OFFLINE'}
                </span>
              </div>
              <div className="w-full h-1.5 bg-gray-50 rounded-full overflow-hidden">
                <div className={`h-full ${health.services?.database === 'up' ? 'bg-green-500 w-full' : 'bg-red-500 w-0'}`} />
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Task Queue (Celery)</span>
                <span className={`text-[10px] font-black ${health.services?.celery === 'up' ? 'text-blue-600' : 'text-amber-600'} uppercase`}>
                  {health.services?.celery === 'up' ? 'ACTIVE' : 'DEGRADED'}
                </span>
              </div>
              <div className="w-full h-1.5 bg-gray-50 rounded-full overflow-hidden">
                <div className={`h-full ${health.services?.celery === 'up' ? 'bg-blue-500 w-full' : 'bg-amber-500 w-1/2'}`} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
