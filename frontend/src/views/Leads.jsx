import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { ChevronLeft, Filter, SortAsc, Bookmark, Search as SearchIcon, Loader2, Flame } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import LeadCard from '../components/LeadCard';
import LeadDetail from '../components/LeadDetail';

const Leads = () => {
  const [searchParams] = useSearchParams();
  const [leads, setLeads] = useState([]);
  const [selectedLead, setSelectedLead] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('search'); // 'search' or 'saved'
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [error, setError] = useState(null);

  const query = searchParams.get('q');
  const radius = searchParams.get('radius');
  const category = searchParams.get('category');
  const hotOnly = searchParams.get('hot') === 'true';
  const leadIdFromUrl = searchParams.get('lead_id');

  const fetchLeads = async () => {
    setLoading(true);
    setError(null);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      // Default to live leads if no specific search query
      let url = `${apiUrl}/leads/search?limit=50&live=true`;
      
      if (view === 'saved') {
        url = `${apiUrl}/leads/search?limit=50&is_saved=true`;
      } else {
        if (query) url += `&query=${encodeURIComponent(query)}`;
        if (radius) url += `&radius=${encodeURIComponent(radius)}`;
        if (category) url += `&category=${encodeURIComponent(category)}`;
        if (hotOnly) url += `&hot_only=true`;
      }

      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);
      
      if (!res.ok) throw new Error('Failed to fetch leads');
      
      const data = await res.json();
      const results = data.results || [];
      setLeads(results);

      // If leadIdFromUrl is present, try to find it in the current results or fetch it
      if (leadIdFromUrl) {
        const found = results.find(l => l.id === leadIdFromUrl);
        if (found) {
          setSelectedLead(found);
        } else {
          // Fetch specific lead if not in results
          try {
            const leadRes = await fetch(`${apiUrl}/leads/${leadIdFromUrl}`);
            if (leadRes.ok) {
              const leadData = await leadRes.json();
              setSelectedLead(leadData);
            }
          } catch (e) {
            console.error("Failed to fetch lead from URL:", e);
          }
        }
      }
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name !== 'AbortError') {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [searchParams, view, hotOnly]);

  const handleToggleSave = async (leadId) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/leads/${leadId}/save`, { method: 'PATCH' });
      if (res.ok) {
        setLeads(leads.map(l => l.id === leadId ? { ...l, is_saved: l.is_saved === 1 ? 0 : 1 } : l));
        if (selectedLead && selectedLead.id === leadId) {
          setSelectedLead({ ...selectedLead, is_saved: selectedLead.is_saved === 1 ? 0 : 1 });
        }
        if (view === 'saved') {
           setLeads(leads.filter(l => l.id !== leadId));
           if (selectedLead && selectedLead.id === leadId) setSelectedLead(null);
        }
      }
    } catch (err) {
      console.error("Failed to toggle save:", err);
    }
  };

  const handleUpdateLead = async (leadId, data) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/leads/${leadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (res.ok) {
        setLeads(leads.map(l => l.id === leadId ? { ...l, ...data } : l));
        if (selectedLead && selectedLead.id === leadId) {
          setSelectedLead({ ...selectedLead, ...data });
        }
      }
    } catch (err) {
      console.error("Failed to update lead:", err);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white p-6">
      {/* Header */}
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/" className="p-2 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-colors">
              <ChevronLeft size={24} />
            </Link>
            <div>
              <h1 className="text-2xl font-black italic tracking-tighter">
                {view === 'saved' ? 'SAVED LEADS' : `SEARCH: "${query || 'All'}"`}
              </h1>
              <p className="text-white/40 text-xs font-bold uppercase tracking-widest mt-1">
                {leads.length} Active Signals Found
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <button 
              onClick={() => setView('search')}
              className={`px-4 py-2 rounded-xl text-sm font-bold uppercase tracking-wider transition-all border ${view === 'search' ? 'bg-white text-black border-white' : 'bg-white/5 text-white/40 border-white/10'}`}
            >
              Search Results
            </button>
            <button 
              onClick={() => setView('saved')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold uppercase tracking-wider transition-all border ${view === 'saved' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white/5 text-white/40 border-white/10'}`}
            >
              <Bookmark size={16} fill={view === 'saved' ? 'currentColor' : 'none'} />
              Saved
            </button>
          </div>
        </div>

        {/* Filters & Sorting */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8 py-4 border-y border-white/5">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm font-medium text-white/60">
              <Filter size={14} />
              <span>Filter:</span>
              <select 
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="bg-transparent outline-none border-none focus:ring-0 cursor-pointer text-white"
              >
                <option value="all">All Intent</option>
                <option value="high">🔥 High Intent</option>
                <option value="medium">Medium Intent</option>
              </select>
            </div>
            
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm font-medium text-white/60">
              <SortAsc size={14} />
              <span>Sort:</span>
              <select 
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-transparent outline-none border-none focus:ring-0 cursor-pointer text-white"
              >
                <option value="newest">Newest First</option>
                <option value="distance">Nearest First</option>
                <option value="intent">Highest Intent</option>
              </select>
            </div>
          </div>

          {view === 'search' && (
             <div className="flex items-center gap-2 px-4 py-1.5 bg-red-500/10 border border-red-500/20 rounded-lg">
                <Flame size={14} className="text-red-500" />
                <span className="text-xs font-bold text-red-500 uppercase tracking-widest">Hot Leads Only</span>
                <div className="w-8 h-4 bg-red-500 rounded-full relative ml-2 cursor-pointer" onClick={() => {/* Toggle hot from here too? */}}>
                  <div className="absolute right-1 top-1 w-2 h-2 rounded-full bg-white" />
                </div>
             </div>
          )}
        </div>

        {/* Results Grid */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <Loader2 size={48} className="animate-spin text-blue-500" />
            <p className="text-white/40 font-bold uppercase tracking-[0.2em] animate-pulse">Scouring Platforms...</p>
          </div>
        ) : error ? (
          <div className="text-center py-24 bg-red-500/5 border border-red-500/10 rounded-3xl">
            <p className="text-red-500 font-bold mb-2">Discovery Failed</p>
            <p className="text-white/40 text-sm">{error}</p>
            <button onClick={fetchLeads} className="mt-4 px-6 py-2 bg-red-500 text-white rounded-xl font-bold">Retry Discovery</button>
          </div>
        ) : leads.length === 0 ? (
          <div className="text-center py-24 bg-white/5 border border-white/10 rounded-3xl">
            <div className="w-16 h-16 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4 text-white/20">
              <SearchIcon size={32} />
            </div>
            <p className="text-white font-bold mb-1 uppercase tracking-widest">No Signals Detected</p>
            <p className="text-white/40 text-sm">Try broadening your search or adjusting filters.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <AnimatePresence>
              {leads.map((lead) => (
                <LeadCard 
                  key={lead.id} 
                  lead={lead} 
                  onSave={handleToggleSave}
                  onClick={setSelectedLead}
                  isSavedView={view === 'saved'}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      <AnimatePresence>
        {selectedLead && (
          <LeadDetail 
            lead={selectedLead} 
            onClose={() => setSelectedLead(null)}
            onSave={handleToggleSave}
            onUpdate={handleUpdateLead}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

export default Leads;