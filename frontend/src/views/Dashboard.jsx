import React, { useState, useEffect, useRef } from 'react';
import { Search, Activity, Target, MessageSquare, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate, useLocation } from 'react-router-dom';
import LeadCard from '../components/LeadCard';
import SuccessTicker from '../components/SuccessTicker';
import MoneyMetrics from '../components/MoneyMetrics';
import LeadsDrawer from '../components/LeadsDrawer';
import { EmptyState } from '../components/UXStates';
import { 
  API_URL, 
  API_KEY, 
  GOOGLE_CSE_ID, 
  fetchLeadsMeta 
} from '../utils/api';

const Dashboard = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState('');
  const [locationStr, setLocationStr] = useState('Kenya');
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [warningMessage, setWarningMessage] = useState('');
  
  // Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState(null);
  const [debugData, setDebugData] = useState(null);
  
  const searchControllerRef = useRef(null);

  // Sync with URL query param
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const q = params.get('q');
    if (q) {
      setQuery(q);
      fetchLeads(q);
    }
  }, [location.search]);

  useEffect(() => {
    fetchLeadsMeta().then(({ leads, warning }) => {
      // User Requested: Frontend Sorting by buyer_match_score
      const sortedLeads = (leads || []).sort((a, b) => (b.buyer_match_score || 0) - (a.buyer_match_score || 0));
      setLeads(sortedLeads);
      setWarningMessage(warning || "");
    });
  }, []);

  const fetchLeads = async (searchQuery, isPolling = false) => {
    // Get or create session ID
    let sessionId = localStorage.getItem('d9_session_id');
    if (!sessionId) {
      sessionId = `sess_${Math.random().toString(36).substring(2, 15)}`;
      localStorage.setItem('d9_session_id', sessionId);
    }

    // If a request is already in progress:
    if (searchControllerRef.current) {
      if (isPolling) {
        // If it's a polling request, just skip to avoid overlapping
        return;
      } else {
        // If it's a foreground request (user search), abort the previous one
        // so we can start the new search immediately
        const oldController = searchControllerRef.current;
        searchControllerRef.current = null; // Clear it before aborting to avoid race conditions
        oldController.abort();
      }
    }

    if (!isPolling) setLoading(true);
    setErrorMessage(''); // Clear previous error
    
    const controller = new AbortController();
    searchControllerRef.current = controller;
    
    // Increased timeout for deep discovery (300s) to align with backend multi-pass strategy
    const timeoutId = setTimeout(() => {
      if (searchControllerRef.current === controller) {
        controller.abort();
      }
    }, 300000);

    try {
      const apiUrl = API_URL;
      const apiKey = API_KEY;
      
      if (!isPolling) {
        setLeads([]);
        setHasSearched(true);
        
        // ABSOLUTE RULE: Real-time discovery with no-store cache
        const searchRes = await fetch(`${apiUrl}/search`, {
          method: 'POST',
          signal: controller.signal,
          headers: { 
            'Content-Type': 'application/json',
            'X-API-Key': apiKey,
            'X-Session-ID': sessionId
          },
          body: JSON.stringify({ 
            query: searchQuery, 
            location: "remote" 
          }),
          cache: 'no-store' // ENFORCED: No cached data
        });
        
        clearTimeout(timeoutId);

        const searchData = await searchRes.json();
        
        if (!searchRes.ok) {
          throw new Error(JSON.stringify(searchData));
        }

        console.log("Success:", searchData);
        if (searchData.warning) setWarningMessage(searchData.warning);
        
        // Capture debug data
        if (searchData.metrics || searchData.rejected) {
            setDebugData({
                metrics: searchData.metrics || {},
                rejected: searchData.rejected || []
            });
        }

        if (searchData.results && searchData.results.length > 0) {
          // User Requested: Frontend Sorting by buyer_match_score
          const sortedResults = [...searchData.results].sort((a, b) => (b.buyer_match_score || 0) - (a.buyer_match_score || 0));
          setLeads(sortedResults);
          setLoading(false);
          return;
        } else if (searchData.status === 'zero_results' || (searchData.results && searchData.results.length === 0)) {
          // USER-FRIENDLY: Handle zero results without throwing a scary error
          setErrorMessage("No verified signals found for this search. Try a broader keyword.");
          setLoading(false);
          return;
        } else if (searchData.message) {
          // Step 6: Zero results rule
          setErrorMessage(searchData.message);
          setLoading(false);
          return;
        } else {
          throw new Error('No live sources returned data.');
        }
      }

      // Fallback or Polling: Fetch from standard leads endpoint
      const res = await fetch(`${apiUrl}/leads?query=${encodeURIComponent(searchQuery)}&limit=10`, {
        signal: controller.signal,
        headers: {
          'X-API-Key': apiKey,
          'X-Session-ID': sessionId
        },
        cache: 'no-store' // ENFORCED: No cached data
      });

      if (!res.ok) {
        const text = await res.text();
        console.error("Backend error:", text);
        throw new Error(text);
      }
      const data = await res.json();
      if (data.warning) setWarningMessage(data.warning);
      // Handle both { leads: [] } and [] formats
      let finalLeads = [];
      if (data && data.leads) {
        finalLeads = data.leads;
      } else {
        finalLeads = Array.isArray(data) ? data : [];
      }

      // User Requested: Frontend Sorting by buyer_match_score
      const sortedLeads = [...finalLeads].sort((a, b) => (b.buyer_match_score || 0) - (a.buyer_match_score || 0));
      setLeads(sortedLeads);
    } catch (err) {
      console.error("REAL ERROR:", err);
      if (err.name === 'AbortError') return;
      console.error("Search failed:", err);
      let msg = err?.message || String(err) || "Backend connection failed. Check if server is running.";
      if (msg === "Failed to fetch") {
         msg += " (Connection Refused or CORS error - Check Backend Logs)";
      }
      setErrorMessage(msg);
    } finally {
      if (!isPolling) setLoading(false);
      if (searchControllerRef.current === controller) {
        searchControllerRef.current = null;
      }
    }
  };

  const handleStatusChange = async (leadId, newStatus) => {
    try {
      const apiUrl = API_URL;
      const apiKey = API_KEY;
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

  // Google CSE script effect
  useEffect(() => {
    if (!GOOGLE_CSE_ID) return;

    const loadCSE = () => {
      const existingScript = document.querySelector(`script[src*="cse.google.com/cse.js"]`);
      if (!existingScript) {
        const script = document.createElement('script');
        script.src = `https://cse.google.com/cse.js?cx=${GOOGLE_CSE_ID}`;
        script.async = true;
        
        script.onerror = (e) => {
          console.warn("Google CSE failed to load. Ad-blocker or network issue likely.", e);
          // Optional: Set a state to show a fallback UI or hide the search box
        };

        document.body.appendChild(script);
      } else {
        // If script is already loaded, try to re-render the element
        if (window.google && window.google.search && window.google.search.cse && window.google.search.cse.element) {
           window.google.search.cse.element.go();
        }
      }
    };

    // Small delay to ensure DOM is ready
    const timer = setTimeout(loadCSE, 100);
    return () => clearTimeout(timer);
  }, []);

  const trendingSearches = [
    { term: 'Toyota', label: 'Toyota' },
    { term: 'House', label: 'Real Estate' },
    { term: 'iPhone', label: 'Electronics' },
    { term: 'Laptop', label: 'Tech' },
    { term: 'Water Tank', label: 'Construction' },
    { term: 'Sofa', label: 'Furniture' },
    { term: 'Solar Panel', label: 'Energy' },
    { term: 'Office Space', label: 'Commercial' }
  ];

  return (
    <div className={`flex-1 flex flex-col bg-black overflow-y-auto ${!hasSearched ? 'justify-start md:justify-center py-12' : 'pt-12'}`}>
      <SuccessTicker onMetricClick={(filter) => {
        setActiveFilter(filter);
        setIsDrawerOpen(true);
      }} />
      <div className="w-full max-w-4xl mx-auto px-4 mb-8">
        {!hasSearched && (
          <div className="text-center mb-12">
            <h1 className="text-5xl font-black text-white tracking-tighter italic mb-4 uppercase">
              🔍 Delta<span className="text-blue-600">9</span>
            </h1>
            <p className="text-white/40 text-[10px] font-black uppercase tracking-[0.5em]">
              Market Intelligence Node
            </p>
          </div>
        )}

        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="flex-1 relative group">
            <Search className="absolute left-6 top-1/2 -translate-y-1/2 h-6 w-6 text-white/20 group-focus-within:text-blue-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleSearch}
              placeholder="Product / Service"
              className="w-full bg-white/5 border border-white/10 text-white text-xl rounded-3xl pl-16 p-6 shadow-2xl outline-none font-black placeholder:text-white/10 italic focus:border-blue-500/50 focus:bg-white/10 transition-all uppercase tracking-tight"
            />
            <div className="absolute right-6 top-1/2 -translate-y-1/2 flex items-center gap-2">
              <span className="hidden md:block text-[8px] font-black text-white/10 uppercase tracking-widest border border-white/5 px-2 py-1 rounded">Strict Mode</span>
            </div>
          </div>
          <div className="w-full md:w-64 relative group">
            <input
              type="text"
              value={locationStr}
              onChange={(e) => setLocationStr(e.target.value)}
              onKeyDown={handleSearch}
              placeholder="Location"
              className="w-full bg-white/5 border border-white/10 text-white text-xl rounded-3xl p-6 shadow-2xl outline-none font-black placeholder:text-white/10 italic focus:border-blue-500/50 focus:bg-white/10 transition-all uppercase tracking-tight"
            />
          </div>
        </div>

        <MoneyMetrics onMetricClick={(filter) => {
          setActiveFilter(filter);
          setIsDrawerOpen(true);
        }} />
        
        {/* User Requested: Live Actionable Leads Section */}
        {leads.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-8 mb-8"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {leads.slice(0, 4).map((lead, index) => {
                const isRecent = lead.timestamp && (new Date() - new Date(lead.timestamp)) < 24 * 60 * 60 * 1000;
                const isHighIntent = lead.intent_score >= 0.8;
                const hasWhatsApp = !!lead.whatsapp_link;
                
                return (
                  <motion.div 
                    key={lead.id || `quick-lead-${index}`} 
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="bg-white/5 border border-white/10 rounded-2xl p-5 hover:border-blue-500/50 transition-all group"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex flex-wrap gap-2">
                        {isHighIntent && (
                          <span className="px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-widest bg-red-500/10 text-red-500 border border-red-500/20">
                            🔥 High intent
                          </span>
                        )}
                        {hasWhatsApp && (
                          <span className="px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-widest bg-green-500/10 text-green-500 border border-green-500/20">
                            💬 WhatsApp
                          </span>
                        )}
                        {isRecent && (
                          <span className="px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-widest bg-blue-500/10 text-blue-500 border border-blue-500/20">
                            ⏱ Recent
                          </span>
                        )}
                      </div>
                      <div className="text-white/40 text-[10px] font-black uppercase tracking-widest bg-white/5 px-2 py-1 rounded">Score: {lead.intent_score || lead.score}</div>
                    </div>
                    
                    <h3 className="text-white font-black text-lg mb-4 italic leading-tight">
                      "{lead.intent?.length > 60 ? lead.intent.substring(0, 60) + '...' : lead.intent}"
                    </h3>

                    <div className="flex gap-3 mt-auto">
                      {lead.whatsapp_url && (
                        <a 
                          href={lead.whatsapp_url} 
                          target="_blank" 
                          rel="noreferrer"
                          className="flex-1 bg-green-600/20 hover:bg-green-600 text-green-500 hover:text-white py-3 rounded-xl text-[10px] font-black uppercase tracking-widest text-center transition-all flex items-center justify-center gap-2 cursor-pointer"
                        >
                          <MessageSquare size={14} /> WhatsApp
                        </a>
                      )}
                      {lead.source_url && (
                        <a 
                          href={lead.source_url} 
                          target="_blank" 
                          rel="noreferrer"
                          className="flex-1 bg-white/5 hover:bg-white/10 text-white/40 hover:text-white py-3 rounded-xl text-[10px] font-black uppercase tracking-widest text-center transition-all flex items-center justify-center gap-2 cursor-pointer"
                        >
                          <Activity size={14} /> Source
                        </a>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
            
            <button 
              onClick={() => {
                setActiveFilter(`/leads?q=${query}`);
                setIsDrawerOpen(true);
              }}
              className="w-full mt-6 py-4 bg-blue-600/10 hover:bg-blue-600 text-blue-500 hover:text-white border border-blue-500/20 hover:border-blue-600 rounded-2xl text-[10px] font-black uppercase tracking-[0.3em] transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              View More Verified Signals <Zap size={14} />
            </button>
          </motion.div>
        )}

        {warningMessage && !hasSearched && (
          <div className="mx-4 mb-4 rounded-2xl bg-yellow-500/10 border border-yellow-500/20 p-4">
            <p className="text-yellow-500 text-xs font-black uppercase tracking-widest">{warningMessage}</p>
          </div>
        )}
        {/* Google CSE Search Box */}
        <div className="gcse-search mb-6"></div>

        {!hasSearched && (
          <div className="flex flex-wrap items-center justify-center gap-3">
            <span className="text-[10px] font-black text-white/20 uppercase tracking-widest mr-2">Trending:</span>
            {trendingSearches.map((item) => (
              <button
                key={item.term}
                onClick={() => {
                  setQuery(item.term);
                  fetchLeads(item.term);
                }}
                className="px-4 py-2 rounded-full bg-white/5 border border-white/10 text-white/40 text-[10px] font-black hover:bg-blue-600 hover:text-white hover:border-blue-600 transition-all uppercase tracking-wider cursor-pointer"
              >
                {item.label}
              </button>
            ))}
          </div>
        )}
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
              {warningMessage && (
                <div className="mx-4 mb-4 rounded-2xl bg-yellow-500/10 border border-yellow-500/20 p-4">
                  <p className="text-yellow-500 text-xs font-black uppercase tracking-widest">{warningMessage}</p>
                </div>
              )}
              
              <div className="grid grid-cols-1 gap-4">
                {errorMessage ? (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8 text-center">
                    <p className="text-white font-bold text-lg">{errorMessage}</p>
                    {warningMessage && (
                      <p className="text-white/40 text-[10px] mt-4 uppercase tracking-tighter">
                        Local development mode enabled. Bypassing strict verification for testing.
                      </p>
                    )}
                    {errorMessage.includes("Failed to fetch") && (
                      <p className="text-blue-400 text-[10px] mt-2 font-bold uppercase">
                        Tip: Ensure backend is running at {API_URL} and check CORS settings.
                      </p>
                    )}
                  </div>
                ) : leads.length > 0 ? leads.map((lead, index) => (
                  <LeadCard key={lead.lead_id || lead.id || `lead-${index}`} lead={lead} onStatusChange={handleStatusChange} />
                )) : (
                  <EmptyState />
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Side Panel for Quick Filtered View */}
      <LeadsDrawer 
        isOpen={isDrawerOpen} 
        onClose={() => setIsDrawerOpen(false)} 
        filterType={activeFilter} 
      />

      {/* Debug Panel */}
      {hasSearched && debugData && (
        <div className="mx-auto max-w-4xl px-4 pb-12">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
                <h3 className="text-white font-bold mb-4 uppercase tracking-widest text-xs">Pipeline Debug Metrics</h3>
                
                <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="bg-black/50 p-4 rounded-xl border border-white/5">
                        <div className="text-white/40 text-[10px] uppercase">Scraped</div>
                        <div className="text-2xl font-black text-blue-500">{debugData.metrics?.scraped || 0}</div>
                    </div>
                    <div className="bg-black/50 p-4 rounded-xl border border-white/5">
                        <div className="text-white/40 text-[10px] uppercase">Passed</div>
                        <div className="text-2xl font-black text-green-500">{leads.length}</div>
                    </div>
                    <div className="bg-black/50 p-4 rounded-xl border border-white/5">
                        <div className="text-white/40 text-[10px] uppercase">Rejected</div>
                        <div className="text-2xl font-black text-red-500">{debugData.metrics?.rejected || debugData.rejected?.length || 0}</div>
                    </div>
                </div>

                {debugData.rejected?.length > 0 && (
                    <div className="space-y-2">
                        <h4 className="text-white/60 font-bold text-[10px] uppercase tracking-widest mb-2">Rejected Signals</h4>
                        <div className="max-h-60 overflow-y-auto space-y-2 pr-2">
                            {debugData.rejected.map((item, idx) => (
                                <div key={idx} className="bg-red-500/5 border border-red-500/10 p-3 rounded-lg">
                                    <div className="flex justify-between items-start mb-1">
                                        <span className="text-red-400 font-bold text-xs">{item.reason || 'Unknown Reason'}</span>
                                        <span className="text-white/20 text-[10px]">{item.source || 'Unknown Source'}</span>
                                    </div>
                                    <p className="text-white/40 text-xs line-clamp-2">{item.text || JSON.stringify(item)}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
