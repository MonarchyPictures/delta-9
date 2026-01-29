import React, { useState, useEffect, useRef } from 'react';
import { Search, Activity, Target } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import LeadCard from '../components/LeadCard';
import getApiUrl, { getApiKey } from '../config';

const Dashboard = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  
  const searchControllerRef = useRef(null);

  const fetchLeads = async (searchQuery, isPolling = false) => {
    // If a request is already in progress:
    if (searchControllerRef.current) {
      if (isPolling) {
        // If it's a polling request, just skip to avoid overlapping
        return;
      } else {
        // If it's a foreground request (user search), abort the previous one
        // so we can start the new search immediately
        searchControllerRef.current.abort();
      }
    }

    if (!isPolling) setLoading(true);
    setErrorMessage(''); // Clear previous error
    
    const controller = new AbortController();
    searchControllerRef.current = controller;

    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      
      if (!isPolling) {
        setLeads([]);
        setHasSearched(true);
        
        // ABSOLUTE RULE: Real-time discovery with no-store cache
        const searchRes = await fetch(`${apiUrl}/search`, {
          method: 'POST',
          signal: controller.signal,
          headers: { 
            'Content-Type': 'application/json',
            'X-API-Key': apiKey
          },
          body: JSON.stringify({ 
            query: searchQuery, 
            location: 'Kenya' 
          }),
          cache: 'no-store' // ENFORCED: No cached data
        });
        
        if (!searchRes.ok) {
          const errorData = await searchRes.json().catch(() => ({ detail: 'Unknown error' }));
          throw new Error(errorData.detail || `Server returned ${searchRes.status}`);
        }

        const searchData = await searchRes.json();
        if (searchData.results && searchData.results.length > 0) {
          setLeads(searchData.results);
          setLoading(false);
          return;
        } else {
          throw new Error('ERROR: No live sources returned data.');
        }
      }

      // Fallback or Polling: Fetch from standard leads endpoint
      const res = await fetch(`${apiUrl}/leads?query=${encodeURIComponent(searchQuery)}&limit=10`, {
        signal: controller.signal,
        headers: {
          'X-API-Key': apiKey
        },
        cache: 'no-store' // ENFORCED: No cached data
      });

      if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
      const data = await res.json();
      setLeads(data);
    } catch (err) {
      if (err.name === 'AbortError') return;
      if (!isPolling) {
        console.error("Discovery error:", err);
        setErrorMessage(err.message || "Failed to fetch leads. Check network connection.");
      }
    } finally {
      if (!isPolling) setLoading(false);
      if (searchControllerRef.current === controller) {
        searchControllerRef.current = null;
      }
    }
  };

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

  const handleSearch = (e) => {
    if (e.key === 'Enter' && query.trim()) fetchLeads(query);
  };

  return (
    <div className={`flex-1 flex flex-col ${!hasSearched ? 'justify-center' : 'pt-12'} bg-black overflow-hidden`}>
      <div className="w-full max-w-4xl mx-auto px-4 mb-8">
        {!hasSearched && (
          <div className="text-center mb-12">
            <h1 className="text-6xl font-black text-white tracking-tighter italic mb-4">
              DELTA<span className="text-blue-600">9</span>
            </h1>
            <p className="text-white/40 text-xs font-black uppercase tracking-[0.4em]">Autonomous Market Intelligence // Kenya</p>
          </div>
        )}

        <div className="relative group">
          <Search className="absolute left-6 top-1/2 -translate-y-1/2 h-6 w-6 text-white/20 group-focus-within:text-blue-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleSearch}
            placeholder="READ: Search Nairobi buyer intent (e.g. 'tires')..."
            className="w-full bg-white/5 border border-white/10 text-white text-xl rounded-3xl pl-16 p-6 shadow-2xl outline-none font-bold placeholder:text-white/20 italic"
          />
        </div>
      </div>

      <AnimatePresence>
        {hasSearched && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex-1 overflow-y-auto px-4 pb-12">
            <div className="max-w-4xl mx-auto">
              <div className="flex items-center justify-between mb-6 px-4">
                <div className="flex items-center gap-2 text-white/40 text-[10px] font-black uppercase tracking-widest">
                  <span className="flex h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse"></span>
                  TAP TO WHATSAPP • UNDER 2 SECONDS
                </div>
                <div className="text-[10px] font-black uppercase tracking-widest text-blue-500">
                  {leads.length} LIVE SIGNALS
                </div>
              </div>
              
              <div className="grid grid-cols-1 gap-4">
                {errorMessage ? (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8 text-center">
                    <p className="text-red-500 font-black uppercase tracking-widest text-sm mb-2">PROD_STRICT PIPELINE FAILED</p>
                    <p className="text-white font-bold text-lg">{errorMessage}</p>
                    <p className="text-white/40 text-xs mt-4 uppercase tracking-tighter">Only independently verified outbound signals are permitted in production.</p>
                  </div>
                ) : leads.length > 0 ? leads.map((lead) => (
                  <LeadCard key={lead.lead_id} lead={lead} onStatusChange={handleStatusChange} />
                )) : null}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Dashboard;