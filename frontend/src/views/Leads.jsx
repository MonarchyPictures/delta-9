import getApiUrl, { getApiKey } from '../config';
import React, { useState, useEffect, useCallback } from 'react';
import { Search, MapPin, Filter, Database, Clock, Zap, MessageSquare } from 'lucide-react';
import LeadCard from '../components/LeadCard';

const Leads = () => {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('Nairobi');
  const [radius, setRadius] = useState('');
  const [timeRange, setTimeRange] = useState('');
  const [highIntent, setHighIntent] = useState(false);
  const [hasWhatsapp, setHasWhatsapp] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchLeads = useCallback(async (isPolling = false) => {
    if (!isPolling) setLoading(true);
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      
      const params = new URLSearchParams({
        location,
        query,
        limit: 50
      });

      if (radius) params.append('radius', radius);
      if (timeRange) params.append('time_range', timeRange);
      if (highIntent) params.append('high_intent', 'true');
      if (hasWhatsapp) params.append('has_whatsapp', 'true');

      const res = await fetch(`${apiUrl}/leads?${params.toString()}`, {
        headers: {
          'X-API-Key': apiKey
        },
        cache: 'no-store' // ENFORCED: No cached data
      });
      if (res.ok) {
        const data = await res.json();
        setLeads(data);
        setLastUpdated(new Date());
      }
    } catch (err) {
      console.error("Fetch leads failed:", err);
    } finally {
      if (!isPolling) setLoading(false);
    }
  }, [location, query, radius, timeRange, highIntent, hasWhatsapp]);

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
              <h1 className="text-4xl font-black text-white italic tracking-tighter uppercase">Market Signals <span className="text-blue-600 text-lg not-italic align-top ml-2">KENYA ONLY</span></h1>
              <div className="flex items-center gap-2 text-white/40 text-xs font-medium uppercase tracking-widest">
                <span className="flex h-2 w-2 rounded-full bg-green-500 animate-pulse"></span>
                Live Intelligence Stream • Updated {Math.floor((new Date() - lastUpdated) / 1000)}s ago
              </div>
            </div>
            
            <div className="relative group w-full md:w-96">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/20 group-focus-within:text-blue-500 transition-colors" />
              <input 
                type="text" 
                placeholder="Search keywords (e.g. 'tires', 'tanks')..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-2xl pl-12 pr-4 py-3 text-white text-base focus:outline-none focus:border-blue-500/50 focus:bg-white/10 transition-all"
              />
            </div>
          </div>

          {/* Advanced Filters Bar */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {/* Radius Filter */}
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <select 
                value={radius}
                onChange={(e) => setRadius(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none appearance-none cursor-pointer hover:bg-white/10 transition-colors"
              >
                <option value="" className="bg-neutral-900">Any Radius</option>
                <option value="5" className="bg-neutral-900">5km (Local)</option>
                <option value="50" className="bg-neutral-900">50km (City)</option>
                <option value="500" className="bg-neutral-900">500km (National)</option>
              </select>
            </div>

            {/* Time Filter */}
            <div className="relative">
              <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <select 
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none appearance-none cursor-pointer hover:bg-white/10 transition-colors"
              >
                <option value="" className="bg-neutral-900">Any Time</option>
                <option value="1h" className="bg-neutral-900">Last 1h</option>
                <option value="24h" className="bg-neutral-900">Last 24h</option>
                <option value="72h" className="bg-neutral-900">Last 72h</option>
              </select>
            </div>

            {/* Intent Filter */}
            <button 
              onClick={() => setHighIntent(!highIntent)}
              className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border transition-all text-sm font-bold ${
                highIntent 
                  ? 'bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-600/20' 
                  : 'bg-white/5 border-white/10 text-white/40 hover:bg-white/10'
              }`}
            >
              <Zap size={16} />
              <span>High Intent</span>
            </button>

            {/* WhatsApp Filter */}
            <button 
              onClick={() => setHasWhatsapp(!hasWhatsapp)}
              className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border transition-all text-sm font-bold ${
                hasWhatsapp 
                  ? 'bg-green-600 border-green-600 text-white shadow-lg shadow-green-600/20' 
                  : 'bg-white/5 border-white/10 text-white/40 hover:bg-white/10'
              }`}
            >
              <MessageSquare size={16} />
              <span>WhatsApp Only</span>
            </button>

            {/* Reset/Status */}
            <div className="hidden md:flex items-center justify-center text-[10px] font-black uppercase tracking-widest text-white/20">
              {leads.length} Signals Found
            </div>
          </div>
        </div>

        {loading && leads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32 space-y-4">
            <div className="w-12 h-12 border-2 border-blue-600/20 border-t-blue-600 rounded-full animate-spin" />
            <div className="text-white/40 font-bold uppercase tracking-widest text-sm animate-pulse">Syncing with Kenya Market Nodes...</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {leads.length > 0 ? (
              leads.map((lead) => (
                <LeadCard key={lead.id} lead={lead} />
              ))
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};

export default Leads;
