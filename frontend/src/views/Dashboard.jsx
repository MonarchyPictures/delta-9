import React, { useState, useEffect } from 'react';
import { 
  Activity, Users, Target, Zap, TrendingUp, ShieldCheck, 
  ArrowUpRight, Clock, MessageSquare, Search, Globe, AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import LeadCard from '../components/LeadCard';

const Dashboard = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchStatus, setSearchStatus] = useState('STRICT');
  const [error, setError] = useState(null);

  useEffect(() => {
    let interval;
    if (hasSearched && query) {
      interval = setInterval(() => {
        fetchLeads(query, true); // true for background polling
      }, 10000);
    }
    return () => clearInterval(interval);
  }, [hasSearched, query]);

  const fetchLeads = async (searchQuery, isPolling = false) => {
    if (!isPolling) setLoading(true);
    setError(null);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      
      // 1. If it's a manual search, trigger a fresh scrape in background
      if (!isPolling) {
        setLeads([]); // Clear previous leads for new search
        setHasSearched(true); // Ensure results view is shown
        fetch(`${apiUrl}/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ query: searchQuery, location: 'Kenya' })
        }).catch(err => console.error("Search trigger failed:", err));
        
        // Give the scraper a 2-second head start before the first fetch
        await new Promise(resolve => setTimeout(resolve, 2000));
      }

      // 2. Fetch results (with fallback logic handled by backend)
      const res = await fetch(`${apiUrl}/leads/search?query=${encodeURIComponent(searchQuery)}&limit=50&live=true&buyer_only=true`);
      if (!res.ok) throw new Error('Failed to fetch leads');
      const data = await res.json();
      setLeads(data.results || []);
      setSearchStatus(data.search_status || 'STRICT');
      setHasSearched(true);
    } catch (err) {
      if (!isPolling) setError(err.message);
    } finally {
      if (!isPolling) setLoading(false);
    }
  };

  const handleSearch = (e) => {
    if (e.key === 'Enter' && query.trim()) {
      fetchLeads(query);
    }
  };

  return (
    <div className={`flex-1 flex flex-col ${!hasSearched ? 'justify-center' : 'pt-12'} transition-all duration-500 bg-black overflow-hidden`}>
      {/* Search Section */}
      <div className={`w-full max-w-4xl mx-auto px-4 ${hasSearched ? 'mb-8' : 'mb-0'}`}>
        {!hasSearched && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-12"
          >
            <h1 className="text-6xl font-black text-white tracking-tighter italic mb-4">
              DELTA<span className="text-blue-600">9</span>
            </h1>
            <p className="text-white/40 text-xs font-black uppercase tracking-[0.4em]">
              Autonomous Market Intelligence
            </p>
          </motion.div>
        )}

        <div className="relative group">
          <div className="absolute inset-y-0 left-6 flex items-center pointer-events-none">
            <Search className={`h-6 w-6 ${hasSearched ? 'text-blue-500' : 'text-white/20'} group-focus-within:text-blue-500 transition-colors`} />
          </div>
          <input
             type="text"
             value={query}
             onChange={(e) => setQuery(e.target.value)}
             onKeyDown={handleSearch}
             placeholder="Search live buyer intent (e.g. 'truck tires', 'land in Kiambu')..."
             className="w-full bg-white/5 border border-white/10 text-white text-xl rounded-3xl focus:ring-4 focus:ring-blue-600/20 focus:border-blue-600/50 block pl-16 p-6 shadow-2xl transition-all hover:bg-white/10 outline-none font-bold placeholder:text-white/20 italic"
           />
          <div className="absolute inset-y-0 right-6 flex items-center pointer-events-none">
            <div className="px-3 py-1.5 bg-white/5 rounded-xl text-[10px] font-black text-white/40 uppercase tracking-widest border border-white/10">
              Enter to Hunt
            </div>
          </div>
        </div>

        {/* No extra filters here, just the search bar */}
      </div>

      {/* Results Section - Scrollable bottom to top */}
      <AnimatePresence mode="wait">
        {loading && leads.length === 0 ? (
          <motion.div 
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex-1 flex flex-col items-center justify-center space-y-8"
          >
            <div className="relative">
              <div className="w-24 h-24 border-4 border-blue-600/20 border-t-blue-600 rounded-full animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-12 h-12 bg-blue-600/10 rounded-full animate-pulse" />
              </div>
            </div>
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-black text-white italic uppercase tracking-tighter">Deploying Discovery Agents</h2>
              <p className="text-white/40 text-[10px] font-black uppercase tracking-[0.3em] animate-pulse">
                Scanning Social Graphs & Market Nodes...
              </p>
            </div>
          </motion.div>
        ) : hasSearched && (
          <motion.div 
            key="results"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex-1 overflow-y-auto no-scrollbar px-4 md:px-8 pb-12"
          >
            <div className="max-w-4xl mx-auto">
              {leads.length > 0 ? (
                <div className="flex flex-col-reverse gap-4">
                  {leads.map((lead, index) => (
                    <LeadCard 
                      key={lead.id || index} 
                      lead={lead} 
                      onClick={(l) => navigate(`/leads?lead_id=${l.id}`)}
                    />
                  ))}
                </div>
              ) : (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-24 bg-white/5 border border-white/10 rounded-3xl"
                >
                  <div className="flex flex-col items-center gap-6">
                    <div className="relative">
                      <Search size={48} className="text-white/20" />
                      <div className="absolute inset-0 bg-blue-600/10 blur-2xl rounded-full" />
                    </div>
                    
                    <div className="space-y-2">
                      <h3 className="text-xl font-black text-white italic uppercase tracking-tighter">No Active Signals Found</h3>
                      <p className="text-white/40 text-sm font-bold uppercase tracking-widest max-w-md mx-auto">
                        Try adjusting your keywords or check back later for new leads.
                      </p>
                    </div>

                    <button 
                      onClick={() => setHasSearched(false)}
                      className="px-8 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
                    >
                      New Discovery
                    </button>
                  </div>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Dashboard;
