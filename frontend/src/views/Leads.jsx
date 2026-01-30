import getApiUrl, { getApiKey } from '../config';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Search, MapPin, Filter, Database, Clock, Zap, MessageSquare } from 'lucide-react';
import LeadCard from '../components/LeadCard';

const Leads = () => {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [location, setLocation] = useState('All');
  const [radius, setRadius] = useState('');
  const [timeRange, setTimeRange] = useState('');
  const [highIntent, setHighIntent] = useState(false); // Default to FALSE to show more signals
  const [hasWhatsapp, setHasWhatsapp] = useState(false); // Default to FALSE to show more signals
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [error, setError] = useState(null);
  
  const abortControllerRef = useRef(null);

  // Debounce query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 500);
    return () => clearTimeout(timer);
  }, [query]);

  const fetchLeads = useCallback(async (isPolling = false) => {
    // If a request is already in progress:
    if (abortControllerRef.current) {
      if (isPolling) {
        // If it's a polling request, skip to avoid overlapping/noise
        return;
      } else {
        // If it's a foreground request (user search/filter), abort the previous one
        // because we need the new results immediately.
        abortControllerRef.current.abort();
      }
    }

    if (!isPolling) setLoading(true);
    setError(null);
    
    const controller = new AbortController();
    abortControllerRef.current = controller;
    
    const timeoutId = setTimeout(() => {
      if (abortControllerRef.current === controller) {
        controller.abort();
      }
    }, 30000);

    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      
      const params = new URLSearchParams({
        location,
        query: debouncedQuery,
        limit: 50
      });

      if (radius) params.append('radius', radius);
      if (timeRange) params.append('time_range', timeRange);
      if (highIntent) params.append('high_intent', 'true');
      if (hasWhatsapp) params.append('has_whatsapp', 'true');

      const res = await fetch(`${apiUrl}/leads?${params.toString()}`, {
        signal: controller.signal,
        headers: {
          'X-API-Key': apiKey
        },
        cache: 'no-store'
      });
      
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        setLeads(data);
        setLastUpdated(new Date());
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${res.status}`);
      }
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') return;
      if (!isPolling) {
        console.error("Fetch leads failed:", err);
        setError(err.message);
      }
    } finally {
      if (!isPolling) setLoading(false);
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
    }
  }, [location, debouncedQuery, radius, timeRange, highIntent, hasWhatsapp]);

  const handleStatusChange = async (leadId, newStatus) => {
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      const res = await fetch(`${apiUrl}/leads/${leadId}/status?status=${newStatus}`, {
        method: 'PATCH',
        headers: {
          'X-API-Key': apiKey
        }
      });
      if (res.ok) {
        setLeads(prev => prev.map(l => l.lead_id === leadId ? { ...l, status: newStatus } : l));
      }
    } catch (err) {
      console.error("Status update failed:", err);
    }
  };

  useEffect(() => {
    fetchLeads();
    const interval = setInterval(() => fetchLeads(true), 15000);
    return () => clearInterval(interval);
  }, [fetchLeads]);

  return (
    <div className="flex-1 bg-black p-4 md:p-8 overflow-y-auto">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex flex-col space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <h1 className="text-4xl font-black text-white italic tracking-tighter uppercase">Market Signals <span className="text-blue-600 text-lg not-italic align-top ml-2">LIVE KENYA</span></h1>
              <div className="flex items-center gap-2 text-white/40 text-[10px] font-black uppercase tracking-widest">
                <span className="flex h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse"></span>
                NO COLD LEADS • NO FAKE DATA • NO GUESSING
              </div>
            </div>
            
            <div className="relative group w-full md:w-96">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/20 group-focus-within:text-blue-500 transition-colors" />
              <input 
                type="text" 
                placeholder="READ: Search keywords..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-2xl pl-12 pr-4 py-3 text-white text-base focus:outline-none focus:border-blue-500/50 focus:bg-white/10 transition-all font-bold italic"
              />
            </div>
          </div>

          {/* Precision Filters Bar */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <select 
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-white text-xs font-black uppercase tracking-widest focus:outline-none appearance-none cursor-pointer hover:bg-white/10 transition-colors"
              >
                <option value="All" className="bg-neutral-900">All Kenya</option>
                <option value="Nairobi" className="bg-neutral-900">Nairobi</option>
                <option value="Mombasa" className="bg-neutral-900">Mombasa</option>
                <option value="Kisumu" className="bg-neutral-900">Kisumu</option>
                <option value="Nakuru" className="bg-neutral-900">Nakuru</option>
                <option value="Eldoret" className="bg-neutral-900">Eldoret</option>
              </select>
            </div>

            <div className="relative">
              <Database className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <select 
                value={radius}
                onChange={(e) => setRadius(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-white text-xs font-black uppercase tracking-widest focus:outline-none appearance-none cursor-pointer hover:bg-white/10 transition-colors"
              >
                <option value="" className="bg-neutral-900">Any Radius</option>
                <option value="5" className="bg-neutral-900">5km (Local)</option>
                <option value="50" className="bg-neutral-900">50km (City)</option>
                <option value="500" className="bg-neutral-900">500km (National)</option>
              </select>
            </div>

            <div className="relative">
              <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <select 
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-white text-xs font-black uppercase tracking-widest focus:outline-none appearance-none cursor-pointer hover:bg-white/10 transition-colors"
              >
                <option value="" className="bg-neutral-900">Last 2h (Active)</option>
                <option value="1h" className="bg-neutral-900">Last 1h</option>
                <option value="24h" className="bg-neutral-900">Last 24h</option>
                <option value="72h" className="bg-neutral-900">Last 72h</option>
              </select>
            </div>

            <button 
              onClick={() => setHighIntent(!highIntent)}
              className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border transition-all text-xs font-black uppercase tracking-widest ${
                highIntent 
                  ? 'bg-red-600 border-red-600 text-white shadow-lg shadow-red-600/20' 
                  : 'bg-white/5 border-white/10 text-white/20 hover:bg-white/10'
              }`}
            >
              <Zap size={14} />
              <span>Hot Only</span>
            </button>

            <button 
              onClick={() => setHasWhatsapp(!hasWhatsapp)}
              className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border transition-all text-xs font-black uppercase tracking-widest ${
                hasWhatsapp 
                  ? 'bg-green-600 border-green-600 text-white shadow-lg shadow-green-600/20' 
                  : 'bg-white/5 border-white/10 text-white/20 hover:bg-white/10'
              }`}
            >
              <MessageSquare size={14} />
              <span>WhatsApp Only</span>
            </button>

            <div className="hidden md:flex items-center justify-center text-[10px] font-black uppercase tracking-widest text-white/20">
              {leads.length} LIVE SIGNALS
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-500 text-sm font-bold flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Zap size={16} className="animate-pulse" />
              <span>{error}</span>
            </div>
            <button 
              onClick={() => fetchLeads()}
              className="px-4 py-1.5 bg-red-500 text-white rounded-lg text-[10px] font-black uppercase tracking-widest hover:bg-red-400 transition-colors"
            >
              Retry Sync
            </button>
          </div>
        )}

        {loading && leads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32 space-y-4">
            <div className="w-12 h-12 border-2 border-blue-600/20 border-t-blue-600 rounded-full animate-spin" />
            <div className="text-white/40 font-bold uppercase tracking-widest text-sm animate-pulse">Syncing with Kenya Market Nodes...</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {leads.length > 0 ? (
              leads.map((lead) => (
                <LeadCard key={lead.lead_id} lead={lead} onStatusChange={handleStatusChange} />
              ))
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};

export default Leads;
