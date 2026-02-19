import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { fetchAgents, fetchAgentLeads, fetchNotifications, fetchNotificationCount, exportAgentLeads } from '../utils/api';
import { Bell, Download, RefreshCw, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';

const LeadsDashboard = () => {
  const [agents, setAgents] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [notificationCount, setNotificationCount] = useState(0);
  const [expandedAgentId, setExpandedAgentId] = useState(null);
  const expandedAgentIdRef = useRef(null);
  const [agentLeads, setAgentLeads] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // Keep ref in sync with state for the interval closure
  useEffect(() => {
    expandedAgentIdRef.current = expandedAgentId;
  }, [expandedAgentId]);

  const loadData = async (isBackground = false) => {
    if (!isBackground) setLoading(true);
    setError(null);
    try {
      // Background poll: Only fetch count to save bandwidth
      // Initial load: Fetch everything
      if (isBackground) {
        const count = await fetchNotificationCount();
        setNotificationCount(count);
        // Also refresh agent list to show status changes
        const agentsData = await fetchAgents();
        setAgents(agentsData);
      } else {
        const [agentsData, notifsData] = await Promise.all([
          fetchAgents(),
          fetchNotifications()
        ]);
        setAgents(agentsData);
        setNotifications(notifsData);
        setNotificationCount(notifsData.length);
      }
      
      // Refresh currently expanded agent's leads if any
      const currentExpandedId = expandedAgentIdRef.current;
      if (currentExpandedId) {
        const leads = await fetchAgentLeads(currentExpandedId);
        setAgentLeads(prev => ({ ...prev, [currentExpandedId]: leads }));
      }
      
      setLastUpdated(new Date());
    } catch (error) {
      console.error("Error loading dashboard data:", error);
      if (!isBackground) setError("Failed to load dashboard data. Please check your connection.");
    } finally {
      if (!isBackground) setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(true), 30000); // 30s refresh
    return () => clearInterval(interval);
  }, []);

  const toggleAgent = async (agentId) => {
    if (expandedAgentId === agentId) {
      setExpandedAgentId(null);
    } else {
      setExpandedAgentId(agentId);
      // Fetch immediately if not present or to ensure freshness
      if (!agentLeads[agentId]) {
        setLoading(true);
        try {
          const leads = await fetchAgentLeads(agentId);
          setAgentLeads(prev => ({ ...prev, [agentId]: leads }));
        } finally {
          setLoading(false);
        }
      }
    }
  };

  const handleExport = async (e, agentId, agentName) => {
    e.stopPropagation();
    const data = await exportAgentLeads(agentId);
    if (data && data.blob) {
      const url = window.URL.createObjectURL(data.blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = data.filename || `leads_${agentName}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }
  };

  return (
    <div className="p-4 md:p-8 bg-gray-900 min-h-screen text-white">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4 mb-8 text-center md:text-left">
        <div>
          <h1 className="text-xl md:text-3xl font-bold text-blue-400 flex flex-col md:flex-row items-center gap-3">
            🎯 Lead Intelligence Dashboard
          </h1>
          <p className="text-gray-400 mt-2">
            Real-time monitoring of agent activities and incoming leads
          </p>
        </div>
        <div className="flex flex-wrap justify-center items-center gap-4">
          <div className="text-sm text-gray-400">
            Last updated: {lastUpdated.toLocaleTimeString()}
          </div>
          <button 
            onClick={loadData} 
            className={`p-2 rounded-full bg-gray-800 hover:bg-gray-700 transition-colors ${loading ? 'animate-spin' : ''}`}
          >
            <RefreshCw size={20} />
          </button>
          <div className="relative">
            <Bell size={24} className="text-yellow-400" />
            {notificationCount > 0 && (
              <span className="absolute -top-2 -right-2 bg-red-500 text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">
                {notificationCount}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => loadData()} className="underline hover:text-red-300">Retry</button>
        </div>
      )}

      {/* Live Notifications Ticker */}
      {notifications.length > 0 && (
        <div className="mb-8 bg-gray-800/50 border border-yellow-500/20 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-yellow-400 mb-2 flex items-center gap-2">
            <Bell size={16} /> Live Alerts
          </h3>
          <div className="space-y-2">
            {notifications.slice(0, 3).map((notif, idx) => (
              <div key={idx} className="flex items-center justify-between text-sm bg-gray-800 p-2 rounded">
                <span>{notif.message}</span>
                <span className="text-gray-500 text-xs">{new Date(notif.created_at).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Agents List */}
      <div className="space-y-4">
        {agents.map(agent => (
          <div key={agent.id} className="bg-gray-800 rounded-xl overflow-hidden border border-gray-700">
            <div 
              className="p-4 flex flex-col md:flex-row items-center justify-between cursor-pointer hover:bg-gray-750 transition-colors gap-4"
              onClick={() => toggleAgent(agent.id)}
            >
              <div className="flex flex-col md:flex-row items-center gap-4 text-center md:text-left">
                {expandedAgentId === agent.id ? <ChevronDown /> : <ChevronRight />}
                <div>
                  <h3 className="text-xl font-bold text-white">{agent.name}</h3>
                  <div className="flex flex-wrap justify-center md:justify-start items-center gap-4 text-sm text-gray-400 mt-1">
                    <span>Query: "{agent.query}"</span>
                    <span>•</span>
                    <span className={agent.active ? "text-green-400" : "text-red-400"}>
                      {agent.active ? "Active" : "Stopped"}
                    </span>
                    <span>•</span>
                    <span>Next Run: {new Date(agent.next_run_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col md:flex-row items-center gap-4 w-full md:w-auto justify-center md:justify-end">
                <div className="text-center md:text-right">
                  <div className="text-2xl font-bold text-blue-400">{agent.leads_count || 0}</div>
                  <div className="text-xs text-gray-500">Total Leads</div>
                </div>
                <button
                  onClick={(e) => handleExport(e, agent.id, agent.name)}
                  className="p-2 bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 rounded-lg transition-colors flex items-center gap-2"
                  title="Export Leads"
                >
                  <Download size={18} />
                  <span className="text-sm font-medium">Export</span>
                </button>
              </div>
            </div>

            {/* Expanded Leads View */}
            {expandedAgentId === agent.id && (
              <div className="border-t border-gray-700 bg-gray-900/50 p-4">
                {agentLeads[agent.id] && agentLeads[agent.id].length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="text-gray-500 border-b border-gray-700">
                          <th className="pb-2 font-medium">Date</th>
                          <th className="pb-2 font-medium">Lead Title / Description</th>
                          <th className="pb-2 font-medium">Source</th>
                          <th className="pb-2 font-medium">Contact</th>
                          <th className="pb-2 font-medium">Score</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                        {agentLeads[agent.id].map((lead) => (
                          <tr key={lead.id} className="group hover:bg-gray-800/50">
                            <td className="py-3 text-gray-400 whitespace-nowrap">
                              {new Date(lead.created_at).toLocaleDateString()}
                            </td>
                            <td className="py-3 font-medium text-white max-w-md truncate" title={lead.title || lead.description}>
                              {lead.title || lead.description}
                            </td>
                            <td className="py-3">
                              <a 
                                href={lead.source_url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-blue-400 hover:text-blue-300 flex items-center gap-1"
                              >
                                Link <ExternalLink size={12} />
                              </a>
                            </td>
                            <td className="py-3 text-gray-300">
                              {lead.contact_info?.phone || "N/A"}
                            </td>
                            <td className="py-3">
                              <div className={`
                                inline-flex px-2 py-0.5 rounded text-xs font-bold
                                ${lead.ranked_score >= 0.7 ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-400'}
                              `}>
                                {Math.round((lead.ranked_score || 0) * 100)}%
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    No leads found for this agent yet.
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        
        {agents.length === 0 && !loading && (
          <div className="text-center py-12 bg-gray-800 rounded-xl border border-dashed border-gray-700">
            <p className="text-gray-400 text-lg">No active agents found.</p>
            <Link to="/agents" className="text-blue-400 hover:text-blue-300 text-sm mt-2 inline-block font-medium">
              Create an agent to start monitoring leads →
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default LeadsDashboard;
