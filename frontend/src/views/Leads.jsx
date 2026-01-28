import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { ChevronLeft, Filter, SortAsc, Bookmark, Search as SearchIcon, Loader2, Flame, ShieldCheck, MapPin, Clock, MessageCircle } from 'lucide-react';
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
  const [searchStatus, setSearchStatus] = useState('STRICT');
  const [seedInput, setSeedInput] = useState('');
  const [radiusFilter, setRadiusFilter] = useState(searchParams.get('radius') || 'anywhere');
  const [timeFilter, setTimeFilter] = useState(searchParams.get('hours') || '24');
  const [whatsappFilter, setWhatsappFilter] = useState('any');
  const [statusFilter, setStatusFilter] = useState('all');

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
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      // Default to live leads if no specific search query
      let url = `${apiUrl}/leads/search?limit=50&live=true`;
      
      if (view === 'saved') {
        url = `${apiUrl}/leads/search?limit=50&is_saved=true`;
      } else {
        if (query) url += `&query=${encodeURIComponent(query)}`;
        if (radiusFilter && radiusFilter !== 'anywhere') url += `&radius=${encodeURIComponent(radiusFilter)}`;
        if (category) url += `&category=${encodeURIComponent(category)}`;
        if (hotOnly) url += `&hot_only=true`;
        if (timeFilter) url += `&hours=${timeFilter}`;
        if (whatsappFilter !== 'any') url += `&has_whatsapp=${whatsappFilter === 'yes'}`;
        if (statusFilter !== 'all') url += `&status=${statusFilter}`;
      }

      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);
      
      if (!res.ok) throw new Error('Failed to fetch leads');
      
      const data = await res.json();
      const results = data.results || [];
      setLeads(results);
      setSearchStatus(data.search_status || 'STRICT');

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
  }, [searchParams, view, hotOnly, radiusFilter, timeFilter, whatsappFilter, statusFilter]);

  const handleToggleSave = async (leadId) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
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

  const handleDeleteLead = async (leadId) => {
    if (!window.confirm("Are you sure you want to discard this lead?")) return;
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/leads/${leadId}`, { method: 'DELETE' });
      if (res.ok) {
        setLeads(leads.filter(l => l.id !== leadId));
        if (selectedLead && selectedLead.id === leadId) setSelectedLead(null);
      }
    } catch (err) {
      console.error("Failed to delete lead:", err);
    }
  };

  const handleUpdateLead = async (leadId, data) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
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
        <div className="flex flex-wrap items-center gap-3 mb-8 py-4 border-y border-white/5">
          {/* Radius Filter */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs font-bold text-white/60">
            <MapPin size={12} className="text-blue-500" />
            <select 
              value={radiusFilter}
              onChange={(e) => setRadiusFilter(e.target.value)}
              className="bg-transparent outline-none border-none focus:ring-0 cursor-pointer text-white uppercase tracking-widest"
            >
              <option value="anywhere" className="text-black bg-white">Anywhere</option>
              <option value="5km" className="text-black bg-white">5km Radius</option>
              <option value="12km" className="text-black bg-white">12km Radius</option>
              <option value="50km" className="text-black bg-white">50km Radius</option>
              <option value="500km" className="text-black bg-white">500km Radius</option>
            </select>
          </div>

          {/* Time Filter */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs font-bold text-white/60">
            <Clock size={12} className="text-blue-500" />
            <select 
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value)}
              className="bg-transparent outline-none border-none focus:ring-0 cursor-pointer text-white uppercase tracking-widest"
            >
              <option value="1" className="text-black bg-white">Last 1h</option>
              <option value="24" className="text-black bg-white">Last 24h</option>
              <option value="72" className="text-black bg-white">Last 72h</option>
              <option value="168" className="text-black bg-white">Last 7 Days</option>
              <option value="720" className="text-black bg-white">Last 30 Days</option>
            </select>
          </div>

          {/* WhatsApp Filter */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs font-bold text-white/60">
            <MessageCircle size={12} className="text-green-500" />
            <select 
              value={whatsappFilter}
              onChange={(e) => setWhatsappFilter(e.target.value)}
              className="bg-transparent outline-none border-none focus:ring-0 cursor-pointer text-white uppercase tracking-widest"
            >
              <option value="any" className="text-black bg-white">Any Contact</option>
              <option value="yes" className="text-black bg-white">WhatsApp Only</option>
            </select>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs font-bold text-white/60">
            <ShieldCheck size={12} className="text-purple-500" />
            <select 
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-transparent outline-none border-none focus:ring-0 cursor-pointer text-white uppercase tracking-widest"
            >
              <option value="all" className="text-black bg-white">All Status</option>
              <option value="new" className="text-black bg-white">🟢 New</option>
              <option value="contacted" className="text-black bg-white">🟡 Contacted</option>
              <option value="replied" className="text-black bg-white">🔵 Replied</option>
              <option value="negotiating" className="text-black bg-white">🟣 Negotiating</option>
              <option value="converted" className="text-black bg-white">✅ Converted</option>
              <option value="dead" className="text-black bg-white">🔴 Dead</option>
            </select>
          </div>

          <div className="flex-1" />

          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs font-bold text-white/60">
            <SortAsc size={14} />
            <select 
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-transparent outline-none border-none focus:ring-0 cursor-pointer text-white uppercase tracking-widest"
            >
              <option value="newest" className="text-black bg-white">Newest</option>
              <option value="distance" className="text-black bg-white">Nearest</option>
              <option value="intent" className="text-black bg-white">Highest Intent</option>
            </select>
          </div>
        </div>

        {/* Status Indicator */}
        {searchStatus !== 'STRICT' && leads.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center gap-3"
          >
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            <p className="text-xs font-bold text-blue-400 uppercase tracking-widest">
              {searchStatus === 'EXPANDED_TIME' && "🕒 Extended History: Showing leads from last 30 days"}
              {searchStatus === 'RELAXED_LOCATION' && "📡 Wide Spectrum: Low activity detected — expanding sources"}
              {searchStatus === 'AI_INFERRED' && "🧠 AI Insights: Synthetic demand signals detected"}
            </p>
          </motion.div>
        )}

        {/* Results Grid */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <Loader2 size={48} className="animate-spin text-blue-500" />
            <p className="text-white/40 font-bold uppercase tracking-[0.2em] animate-pulse">
              {searchStatus === 'STRICT' ? "Scouring Platforms..." : "Expanding Search Radius..."}
            </p>
          </div>
        ) : error ? (
          <div className="text-center py-24 bg-red-500/5 border border-red-500/10 rounded-3xl">
            <p className="text-red-500 font-bold mb-2">Discovery Failed</p>
            <p className="text-white/40 text-sm">{error}</p>
            <button onClick={fetchLeads} className="mt-4 px-6 py-2 bg-red-500 text-white rounded-xl font-bold">Retry Discovery</button>
          </div>
        ) : leads.length === 0 ? (
          <div className="max-w-2xl mx-auto">
            <div className="text-center py-16 bg-white/5 border border-white/10 rounded-3xl mb-8">
              <div className="w-20 h-20 bg-white/5 rounded-3xl flex items-center justify-center mx-auto mb-6 text-white/20">
                <SearchIcon size={40} />
              </div>
              <h3 className="text-xl font-black italic tracking-tighter mb-2">NO SIGNALS DETECTED</h3>
              <div className="space-y-2 mb-8">
                <p className="text-white/40 text-sm font-bold uppercase tracking-widest flex items-center justify-center gap-2">
                  <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full animate-pulse" />
                  Scanning wider radius...
                </p>
                <p className="text-white/40 text-sm font-bold uppercase tracking-widest">
                  Expanding sources & historical data
                </p>
              </div>

              {/* Seed Search */}
              <div className="px-8">
                <div className="bg-white/5 border border-white/10 p-6 rounded-2xl text-left">
                  <h4 className="text-sm font-black uppercase tracking-widest mb-4 flex items-center gap-2">
                    <Flame size={16} className="text-orange-500" />
                    Seed the Radar
                  </h4>
                  <p className="text-white/40 text-xs font-bold mb-4 uppercase leading-relaxed">
                    Tell us what you're selling. Our AI will hunt for related intent signals across all platforms.
                  </p>
                  <div className="flex gap-2">
                    <input 
                      type="text"
                      value={seedInput}
                      onChange={(e) => setSeedInput(e.target.value)}
                      placeholder="e.g. 2-bedroom apartment in Ruaka"
                      className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-blue-500 outline-none transition-colors"
                    />
                    <button 
                      onClick={() => {
                        if (seedInput) {
                          window.location.href = `/leads?q=${encodeURIComponent(seedInput)}`;
                        }
                      }}
                      className="px-6 py-3 bg-blue-600 text-white rounded-xl font-black uppercase text-[10px] tracking-widest hover:bg-blue-700 transition-all active:scale-95 shadow-lg shadow-blue-600/20"
                    >
                      Track
                    </button>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-center gap-4">
                  <button className="text-[10px] font-black uppercase tracking-widest text-white/20 hover:text-white/40 transition-colors flex items-center gap-2">
                    <Bookmark size={12} />
                    Save Search
                  </button>
                  <div className="w-1 h-1 bg-white/10 rounded-full" />
                  <button className="text-[10px] font-black uppercase tracking-widest text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-2">
                    <ShieldCheck size={12} />
                    Alert Me on WhatsApp
                  </button>
                </div>
              </div>
            </div>

            {/* Fallback Ideas */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-6 bg-white/5 border border-white/10 rounded-2xl">
                <h5 className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40 mb-3">Nearby Regions</h5>
                <div className="flex flex-wrap gap-2">
                  {['Nairobi', 'Mombasa', 'Kisumu', 'Eldoret'].map(city => (
                    <Link key={city} to={`/leads?q=${query || ''}&location=${city}`} className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-bold transition-colors">
                      {city}
                    </Link>
                  ))}
                </div>
              </div>
              <div className="p-6 bg-white/5 border border-white/10 rounded-2xl">
                <h5 className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40 mb-3">Popular Intent</h5>
                <div className="flex flex-wrap gap-2">
                  {['Real Estate', 'Automotive', 'Electronics', 'Services'].map(cat => (
                    <Link key={cat} to={`/leads?category=${cat}`} className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-bold transition-colors">
                      {cat}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <AnimatePresence>
              {leads.map((lead) => (
                <LeadCard 
                  key={lead.id} 
                  lead={lead} 
                  onSave={handleToggleSave}
                  onDelete={handleDeleteLead}
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
            onDelete={handleDeleteLead}
            onUpdate={handleUpdateLead}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

export default Leads;