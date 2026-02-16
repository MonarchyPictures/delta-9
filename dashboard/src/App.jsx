import { useEffect, useState } from "react"; 
import axios from "axios"; 

const API = "http://localhost:8000"; 

function LeadDashboard() { 
  const [agents, setAgents] = useState([]); 
  const [notifications, setNotifications] = useState([]); 
  const [error, setError] = useState(null);

  useEffect(() => { 
    fetchData();
  }, []); 

  const fetchData = async () => {
    setError(null);
    try {
      await Promise.all([fetchAgents(), fetchNotifications()]);
    } catch (err) {
      setError("Failed to connect to backend service.");
    }
  };

  const fetchAgents = async () => { 
    try {
      const res = await axios.get(`${API}/agents`); 
      setAgents(res.data); 
    } catch (error) {
      console.error("Error fetching agents:", error);
      throw error;
    }
  }; 

  const fetchNotifications = async () => { 
    try {
      const res = await axios.get(`${API}/notifications`); 
      setNotifications(res.data); 
    } catch (error) {
      console.error("Error fetching notifications:", error);
      throw error;
    }
  }; 

  const exportLeads = (agentId) => { 
    window.open(`${API}/agents/${agentId}/export`, "_blank"); 
  }; 

  const unreadCount = notifications.filter(n => !n.read).length; 

  return ( 
    <div> 
      <h1>Lead Intelligence Dashboard</h1> 
      
      {error && (
        <div style={{ padding: '10px', backgroundColor: '#ffebee', color: '#c62828', marginBottom: '20px', borderRadius: '4px' }}>
          ⚠️ {error}
        </div>
      )}

      <div style={{ marginBottom: 20 }}> 
        🔔 Notifications: {unreadCount} 
      </div> 

      {agents.map(agent => ( 
        <div 
          key={agent.id} 
          className="bg-slate-800 rounded-2xl p-6 shadow-xl border border-slate-700 hover:border-blue-500 transition-all mb-6"
        > 
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="text-blue-400 font-semibold tracking-wide uppercase text-sm"> 
                {agent.query} 
              </h3> 
              <p className="text-xl font-bold mt-2 text-white"> 
                "{agent.name}" 
              </p>
            </div>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${agent.active ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
              {agent.active ? "Active" : "Paused"}
            </span>
          </div>
          
          <div className="text-slate-400 text-sm mb-6 space-y-2">
            <p>📍 {agent.location}</p>
          </div>

          <button 
            onClick={() => exportLeads(agent.id)}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors"
          > 
            Export Leads 
          </button> 
        </div> 
      ))} 
    </div> 
  ); 
} 

export default function App() { 
  return ( 
    <div className="dashboard-container"> 
      <LeadDashboard /> 
    </div> 
  ) 
}
