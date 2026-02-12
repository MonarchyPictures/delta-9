import React, { useState, useEffect } from 'react';
import { fetchAgents, createAgent, deleteAgent, exportAgentLeads } from '../utils/api';

const AgentManager = () => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    query: '',
    location: 'Kenya',
    interval_hours: 2,
    duration_days: 7,
    min_intent_score: 0.7
  });

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    setLoading(true);
    const data = await fetchAgents();
    setAgents(data);
    setLoading(false);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setLoading(true);
    const result = await createAgent(formData);
    if (result && !result.error) {
      setAgents([...agents, result]);
      setShowCreate(false);
      setFormData({
        name: '',
        query: '',
        location: 'Kenya',
        interval_hours: 2,
        duration_days: 7,
        min_intent_score: 0.7
      });
    }
    setLoading(false);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this agent?')) {
      await deleteAgent(id);
      setAgents(agents.filter(a => a.id !== id));
    }
  };

  const handleExport = async (id) => {
    const data = await exportAgentLeads(id);
    if (data && data.blob) {
      const url = window.URL.createObjectURL(data.blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = data.filename || `agent_${id}_export.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }
  };

  return (
    <div className="p-4 bg-gray-900 text-white rounded-lg shadow-xl">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-blue-400">🕵️ 24/7 Demand Radar Agents</h2>
        <button 
          onClick={() => setShowCreate(!showCreate)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors"
        >
          {showCreate ? 'Cancel' : '+ Create Agent'}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-gray-800 p-6 rounded-lg mb-8 border border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Agent Name</label>
              <input 
                type="text" 
                placeholder="e.g. Water Tanks Hunter"
                className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Search Query</label>
              <input 
                type="text" 
                placeholder="e.g. water tanks"
                className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
                value={formData.query}
                onChange={(e) => setFormData({...formData, query: e.target.value})}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Location</label>
              <input 
                type="text" 
                className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
                value={formData.location}
                onChange={(e) => setFormData({...formData, location: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Run Interval (Hours)</label>
              <select 
                className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
                value={formData.interval_hours}
                onChange={(e) => setFormData({...formData, interval_hours: parseInt(e.target.value)})}
              >
                <option value={1}>Every 1 Hour</option>
                <option value={2}>Every 2 Hours</option>
                <option value={6}>Every 6 Hours</option>
                <option value={12}>Every 12 Hours</option>
                <option value={24}>Every 24 Hours</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Duration (Days)</label>
              <input 
                type="number" 
                className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
                value={formData.duration_days}
                onChange={(e) => setFormData({...formData, duration_days: parseInt(e.target.value)})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Min Intent Score (0.0 - 1.0)</label>
              <input 
                type="number" 
                step="0.1"
                min="0"
                max="1"
                className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
                value={formData.min_intent_score}
                onChange={(e) => setFormData({...formData, min_intent_score: parseFloat(e.target.value)})}
              />
            </div>
          </div>
          <button 
            type="submit" 
            disabled={loading}
            className="mt-6 w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 rounded transition-colors disabled:opacity-50"
          >
            {loading ? 'Deploying Agent...' : '🚀 Deploy Agent'}
          </button>
        </form>
      )}

      {loading && !showCreate ? (
        <div className="text-center py-10">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-400">Loading your agents...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {agents.length === 0 ? (
            <div className="text-center py-10 bg-gray-800 rounded-lg border border-dashed border-gray-700">
              <p className="text-gray-500">No active agents. Create one to start 24/7 monitoring.</p>
            </div>
          ) : (
            agents.map(agent => (
              <div key={agent.id} className="bg-gray-800 p-4 rounded-lg border border-gray-700 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center">
                    {agent.name}
                    {agent.unread_count > 0 && (
                      <span className="ml-2 px-1.5 py-0.5 bg-blue-600 text-white text-[10px] font-black rounded-md animate-pulse">
                        {agent.unread_count} NEW
                      </span>
                    )}
                    <span className={`ml-3 px-2 py-0.5 text-xs rounded ${agent.is_active ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                      {agent.is_active ? 'ACTIVE' : 'EXPIRED'}
                    </span>
                  </h3>
                  <p className="text-sm text-gray-400 mt-1">
                    🔍 Query: <span className="text-blue-300">"{agent.query}"</span> | 📍 {agent.location}
                  </p>
                  <div className="flex gap-4 mt-2 text-xs text-gray-500">
                    <span>⏱️ Every {agent.interval_hours}h</span>
                    <span>⏳ For {agent.duration_days} days</span>
                    <span>🎯 Intent ≥ {agent.min_intent_score}</span>
                  </div>
                </div>
                
                <div className="flex gap-2">
                  <button 
                    onClick={() => handleExport(agent.id)}
                    className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1.5 rounded text-sm flex items-center"
                    title="Export Leads"
                  >
                    📥 Export .txt
                  </button>
                  <button 
                    onClick={() => handleDelete(agent.id)}
                    className="bg-red-900/50 hover:bg-red-900 text-red-300 px-3 py-1.5 rounded text-sm"
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default AgentManager;
