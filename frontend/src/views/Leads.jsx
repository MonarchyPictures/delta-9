import getApiUrl, { getApiKey } from '../config';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Search, MapPin, Filter, Database, Clock, Zap, MessageSquare, List, Table, Download } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import LeadCard from '../components/LeadCard';
import LeadTable from '../components/LeadTable';
import { EmptyState } from '../components/UXStates';

const Leads = () => {
  const locationState = useLocation();
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
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'table'
  const [selected, setSelected] = useState([]);

  const downloadSelectedLeads = () => {
    const selectedData = leads.filter(l => selected.includes(l.lead_id || l.id));
    
    const content = selectedData.map(l => `
Source: ${l.source_name || l.source_url || "N/A"}
Product: ${l.product || "N/A"}
Location: ${l.location_raw || l.property_city || "N/A"}
Text: ${l.intent || l.intent_query || "N/A"}
Phone: ${l.phone || "N/A"}
Intent Score: ${l.buyer_match_score || l.intent_score || 0}
WhatsApp: ${l.whatsapp_url || l.whatsapp_link || "N/A"}
---
    `).join("\n");

    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `delta9-leads-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportLeadsFromBackend = async () => {
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      
      const res = await fetch(`${apiUrl}/leads/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({ ids: selected })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const contentDisposition = res.headers.get('Content-Disposition');
        let filename = `delta9-export-${new Date().toISOString().split('T')[0]}.txt`;
        if (contentDisposition && contentDisposition.includes('filename=')) {
          filename = contentDisposition.split('filename=')[1].replace(/"/g, '');
        }
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Export failed');
      }
    } catch (err) {
      console.error("Backend export failed:", err);
      alert(`Export failed: ${err.message}`);
    }
  };
  
  const abortControllerRef = useRef(null);

  // Sync with URL query params
  useEffect(() => {
    const params = new URLSearchParams(locationState.search);
    const q = params.get('q');
    const tr = params.get('time_range');
    const hi = params.get('high_intent');
    const wa = params.get('has_whatsapp');
    const loc = params.get('location');

    if (q) setQuery(q);
    if (tr) setTimeRange(tr);
    if (hi === 'true') setHighIntent(true);
    if (wa === 'true') setHasWhatsapp(true);
    if (loc) setLocation(loc);
  }, [locationState.search]);

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
        // If it's a polling request and a foreground request is active, skip
        // but ONLY if the foreground request is relatively fresh (less than 30s)
        if (abortControllerRef.current.startTime && (Date.now() - abortControllerRef.current.startTime < 30000)) {
          return;
        }
      } else {
        // If it's a foreground request (user search/filter), abort the previous one
        // because we need the new results immediately.
        const oldController = abortControllerRef.current;
        abortControllerRef.current = null; // Clear it before aborting to avoid race conditions
        oldController.abort();
      }
    }

    if (!isPolling) setLoading(true);
    setError(null);
    
    const controller = new AbortController();
    controller.startTime = Date.now();
    abortControllerRef.current = controller;
    
    const timeoutId = setTimeout(() => {
      if (abortControllerRef.current === controller) {
        controller.abort();
      }
    }, 100000); // Increased to 100s for reliability

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
        // Handle the Zero Results Rule response from backend
        if (data && data.leads) {
          // AUTO-ADJUST: If no leads found in 2h window, automatically switch to 24h
          if ((!timeRange || timeRange === '2h' || timeRange === '') && data.leads.length === 0) {
             console.log("No leads in 2h window, auto-switching to 24h...");
             setTimeRange('24h');
             return; // The useEffect dependency will trigger a new fetch
          }
          
          // RANKING ALREADY HANDLED BY BACKEND: High-value leads float automatically
          const sortedLeads = (data.leads || []).sort((a, b) => (b.buyer_match_score || 0) - (a.buyer_match_score || 0));
          setLeads(sortedLeads);
        } else {
          const rawLeads = (Array.isArray(data) ? data : []).sort((a, b) => (b.buyer_match_score || 0) - (a.buyer_match_score || 0));
          setLeads(rawLeads);
        }
        setLastUpdated(new Date());
      } else {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${res.status}`);
      }
    } catch (err) {
      clearTimeout(timeoutId);
      // ABSOLUTELY SILENT on AbortError to prevent console clutter
      if (err.name === 'AbortError') return;
      
      if (!isPolling) {
        console.debug("Fetch leads failed or cancelled:", err.message);
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
        setLeads(prev => prev.map(l => (l.lead_id === leadId || l.id === leadId) ? { ...l, status: newStatus } : l));
      }
    } catch (err) {
      console.error("Status update failed:", err);
    }
  };

  const handleTap = async (leadId) => {
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      const res = await fetch(`${apiUrl}/leads/${leadId}/tap`, {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey
        }
      });
      if (res.ok) {
        const data = await res.json();
        setLeads(prev => prev.map(l => 
          (l.lead_id === leadId || l.id === leadId) 
            ? { ...l, status: data.lead_status, tap_count: data.tap_count } 
            : l
        ));
      }
    } catch (err) {
      console.error("Tap tracking failed:", err);
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
            
            <div className="flex items-center gap-2">
              <div className="flex bg-white/5 border border-white/10 p-1 rounded-xl">
                <button 
                  onClick={() => setViewMode('list')}
                  className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-blue-600 text-white' : 'text-white/40 hover:text-white'}`}
                  title="List View"
                >
                  <List size={16} />
                </button>
                <button 
                  onClick={() => setViewMode('table')}
                  className={`p-2 rounded-lg transition-all ${viewMode === 'table' ? 'bg-blue-600 text-white' : 'text-white/40 hover:text-white'}`}
                  title="Table View"
                >
                  <Table size={16} />
                </button>
              </div>

              {selected.length > 0 && (
                <div className="flex items-center gap-2 animate-in fade-in slide-in-from-right-4">
                  <button 
                    onClick={downloadSelectedLeads}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
                    title="Fast Frontend Download"
                  >
                    <Download size={14} />
                    Fast ({selected.length})
                  </button>
                  <button 
                    onClick={exportLeadsFromBackend}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
                    title="Full Backend Export"
                  >
                    <Database size={14} />
                    Export
                  </button>
                </div>
              )}
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
              className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border transition-all text-xs font-black uppercase tracking-widest cursor-pointer ${
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
              className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border transition-all text-xs font-black uppercase tracking-widest cursor-pointer ${
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
          <>
            {leads.length > 0 ? (
              viewMode === 'list' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {leads.map((lead, index) => (
                    <LeadCard 
                      key={lead.lead_id || lead.id || `lead-${index}`} 
                      lead={lead} 
                      onStatusChange={handleStatusChange} 
                      onTap={handleTap} 
                    />
                  ))}
                </div>
              ) : (
                <LeadTable 
                  leads={leads} 
                  selected={selected} 
                  setSelected={setSelected} 
                  onStatusChange={handleStatusChange}
                  onTap={handleTap}
                />
              )
            ) : (
              <div className="flex flex-col items-center justify-center py-20 bg-white/5 border border-white/10 rounded-3xl space-y-6 text-center">
                <div className="p-6 bg-white/5 rounded-full">
                  <Database className="w-12 h-12 text-white/20" />
                </div>
                <div className="space-y-2 px-6">
                  <h3 className="text-xl font-black text-white uppercase tracking-tighter italic">
                    {hasWhatsapp && leads.length === 0 
                      ? "No WhatsApp taps yet — signals still warming up"
                      : `No buyer intent detected in the last ${timeRange === '24h' ? '24' : (timeRange === '72h' ? '72' : (timeRange === '1h' ? '1' : '2'))} hours`
                    }
                  </h3>
                  <p className="text-white/40 text-sm max-w-md mx-auto">
                    {hasWhatsapp && leads.length === 0
                      ? "The system is currently aggregating live WhatsApp engagement signals from verified buyers. Check back in a few minutes."
                      : "The engine has strictly filtered out all suppliers, agents, and stale signals. Only real-time demand is allowed."
                    }
                  </p>
                </div>
                <div className="flex flex-col items-center gap-4">
                  <span className="text-[10px] font-black text-blue-500 uppercase tracking-widest">System Suggestion</span>
                  {(!timeRange || timeRange === '2h' || timeRange === '' || timeRange === '1h') ? (
                    <button 
                      onClick={() => setTimeRange('24h')}
                      className="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-lg shadow-blue-600/20 active:scale-95 cursor-pointer"
                    >
                      Widen Time Window (24h)
                    </button>
                  ) : (
                    <button 
                      onClick={() => setTimeRange('72h')}
                      className="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-lg shadow-blue-600/20 active:scale-95 cursor-pointer"
                    >
                      Widen Time Window (72h)
                    </button>
                  )}
                  <p className="text-[10px] text-white/20 uppercase tracking-widest">DO NOT BROADEN INTENT RULES</p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Leads;
