import React from 'react';
import { Search, MapPin, Zap, Shield, Globe, Activity, ArrowRight, Target, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import SummaryCards from '../components/SummaryCards';
import LiveFeed from '../components/LiveFeed';

const Radar = ({ onSearch, stats, leads = [] }) => {
  const [query, setQuery] = React.useState('');
  const [location, setLocation] = React.useState('Kenya');
  const [liveResults, setLiveResults] = React.useState([]);
  const [localLeads, setLocalLeads] = React.useState(leads);
  // Fetch initial leads if not provided
  React.useEffect(() => {
    if (leads && leads.length > 0) {
      setLocalLeads(leads);
      return;
    }

    const controller = new AbortController();
    const fetchInitialLeads = async () => {
      const timeoutId = setTimeout(() => controller.abort(), 8000);
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/leads/search?limit=10`, {
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          const data = await res.json();
          setLocalLeads(data.results || []);
        }
      } catch (err) {
        clearTimeout(timeoutId);
        if (err.name !== 'AbortError') {
          console.error("Initial leads fetch failed:", err);
        }
      }
    };
    fetchInitialLeads();
    return () => controller.abort();
  }, [leads]);
  const [isSearching, setIsSearching] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [showResults, setShowResults] = React.useState(false);
  const [hasSearched, setHasSearched] = React.useState(false);
  const [celeryStatus, setCeleryStatus] = React.useState('up');
  const searchRef = React.useRef(null);
  const searchInputRef = React.useRef(null);
  const locationInputRef = React.useRef(null);

  // Check health status
  React.useEffect(() => {
    const controller = new AbortController();
    const checkHealth = async (signal) => {
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/health`, {
          signal: signal
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          const data = await res.json();
          setCeleryStatus(data.services?.celery || 'up');
        }
      } catch (err) {
        clearTimeout(timeoutId);
        if (err.name !== 'AbortError') {
          console.warn("Health check failed:", err);
        }
      }
    };
    checkHealth(controller.signal);
    const interval = setInterval(() => {
      const intervalController = new AbortController();
      checkHealth(intervalController.signal);
    }, 30000);
    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, []);

  // Debounced search for live results
  React.useEffect(() => {
    const controller = new AbortController();
    
    const timer = setTimeout(async () => {
      if (query.length > 2) {
        setIsSearching(true);
        const requestController = new AbortController();
        const timeoutId = setTimeout(() => requestController.abort(), 8000);
        
        try {
          const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
          const res = await fetch(`${apiUrl}/leads/search?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}&limit=5`, {
            signal: requestController.signal
          });
          clearTimeout(timeoutId);
          if (res.ok) {
            const data = await res.json();
            setLiveResults(data.results || []);
            setShowResults(true);
          }
        } catch (err) {
          clearTimeout(timeoutId);
          if (err.name === 'AbortError') return;
          console.error("Live search failed:", err);
        } finally {
          setIsSearching(false);
        }
      } else {
        setLiveResults([]);
        setShowResults(false);
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, location]);

  // Click outside to close results
  React.useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowResults(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredLeads = React.useMemo(() => {
    // If we haven't searched, show all available leads (global feed)
    if (!hasSearched) return localLeads;
    
    // If we have searched, filter them based on query
    if (!query.trim()) return localLeads;
    return localLeads.filter(lead => 
      lead.buyer_request_snippet?.toLowerCase().includes(query.toLowerCase()) ||
      lead.buyer_name?.toLowerCase().includes(query.toLowerCase())
    );
  }, [localLeads, query, hasSearched]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || isSubmitting) return;
    
    setIsSubmitting(true);
    setShowResults(false);
    
    try {
      // We stay on dashboard to show the "live feed of results"
      // but we still trigger the background search in App
      if (onSearch) {
        await onSearch(query, location, null, false);
      }
      setHasSearched(true);
    } catch (err) {
      console.error("Search submission failed:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`flex-1 overflow-y-auto no-scrollbar py-8 space-y-10 relative ${!hasSearched ? 'min-h-[calc(100vh-64px)]' : ''}`}>
      {/* Celery Down Warning */}
      <AnimatePresence>
        {celeryStatus === 'down' && (
          <div className="max-w-[75%] mx-auto px-4">
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-4 p-5 bg-amber-50 border border-amber-200 rounded-3xl text-amber-800"
            >
              <div className="p-3 bg-amber-100 rounded-2xl">
                <Activity size={20} />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-black uppercase tracking-widest">Discovery Engine Offline</p>
                <p className="text-xs font-bold text-amber-700/80 uppercase tracking-tight">
                  New leads cannot be searched in real-time. Showing cached results only.
                </p>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Simple Search Section - Moves with page */}
      <div className="flex flex-col items-center gap-8 relative z-[1000]" ref={searchRef}>
        {!hasSearched && (
          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <h1 className="text-5xl font-black text-gray-900 tracking-tighter uppercase italic">
              Market <span className="text-blue-600">Discovery</span>
            </h1>
            <p className="text-xs font-bold text-gray-400 uppercase tracking-[0.4em] mt-2">
              Enterprise Lead Generation Engine (Internal Tool)
            </p>
          </motion.div>
        )}
        
        <div className="w-full md:w-[75%] lg:w-[65%] relative">
          <motion.div 
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="bg-white p-3 rounded-[3rem] border border-gray-200 shadow-[0_30px_100px_rgba(0,0,0,0.12)] hover:shadow-[0_40px_120px_rgba(0,0,0,0.15)] transition-shadow duration-500"
          >
            <form onSubmit={handleSubmit} className="flex flex-col md:flex-row items-center gap-3">
              <div 
                className="flex-[2.5] w-full flex items-center gap-4 px-8 py-6 bg-gray-50 rounded-[2.5rem] border border-transparent focus-within:border-blue-500/40 focus-within:bg-white focus-within:shadow-[0_0_40px_rgba(59,130,246,0.12)] transition-colors duration-300 relative group cursor-text"
                onClick={() => searchInputRef.current?.focus()}
              >
                <div className="w-12 h-12 rounded-2xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-600/20 group-focus-within:scale-110 transition-all duration-300 pointer-events-none">
                  <Search size={22} />
                </div>
                <div className="flex-1 relative">
                  <p className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-1 group-focus-within:text-blue-500 transition-colors pointer-events-none">Discovery Query</p>
                  <input 
                    ref={searchInputRef}
                    type="text" 
                    placeholder="What are you looking for?" 
                    className="bg-transparent border-none outline-none w-full text-xl font-bold placeholder:text-gray-300 focus:ring-0 p-0 leading-tight block relative z-10 pointer-events-auto"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => query.length > 2 && setShowResults(true)}
                    onClick={(e) => e.stopPropagation()}
                    autoComplete="off"
                  />
                </div>
                {isSearching && (
                  <div className="absolute right-8 animate-spin w-6 h-6 border-3 border-blue-500/20 border-t-blue-500 rounded-full z-10 pointer-events-none" />
                )}
              </div>

              <div className="hidden md:block w-px h-12 bg-gray-200/50" />

              <div 
                className="flex-1 w-full flex items-center gap-4 px-8 py-6 bg-gray-50 rounded-[2.5rem] border border-transparent focus-within:border-blue-500/40 focus-within:bg-white focus-within:shadow-[0_0_40px_rgba(59,130,246,0.12)] transition-colors duration-300 relative group cursor-text"
                onClick={() => locationInputRef.current?.focus()}
              >
                <div className="w-12 h-12 rounded-2xl bg-gray-100 flex items-center justify-center text-gray-500 group-focus-within:bg-blue-600 group-focus-within:text-white group-focus-within:shadow-lg group-focus-within:shadow-blue-600/20 transition-all duration-300 pointer-events-none">
                  <MapPin size={22} />
                </div>
                <div className="flex-1 relative">
                  <p className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-1 group-focus-within:text-blue-500 transition-colors pointer-events-none">Location</p>
                  <input 
                    ref={locationInputRef}
                    type="text" 
                    placeholder="Global" 
                    className="bg-transparent border-none outline-none w-full text-xl font-bold placeholder:text-gray-300 focus:ring-0 p-0 leading-tight block relative z-10 pointer-events-auto"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    autoComplete="off"
                  />
                </div>
              </div>

              <button 
                type="submit" 
                disabled={isSubmitting}
                className="w-full md:w-auto bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white px-10 py-6 rounded-[2.5rem] font-black uppercase tracking-[0.2em] text-xs transition-all duration-300 flex items-center justify-center gap-3 shadow-[0_20px_40px_rgba(37,99,235,0.3)] hover:shadow-[0_25px_50px_rgba(37,99,235,0.4)] active:scale-95 group overflow-hidden relative"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                {isSubmitting ? (
                  <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Zap size={20} className="group-hover:scale-125 transition-transform" />
                )}
                <span className="relative text-sm">{isSubmitting ? 'Searching...' : 'Search'}</span>
              </button>
            </form>
          </motion.div>

          {/* Live Results Dropdown */}
          <AnimatePresence>
            {showResults && liveResults.length > 0 && (
              <motion.div 
                initial={{ opacity: 0, y: 20, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 20, scale: 0.98 }}
                className="absolute left-0 right-0 top-full mt-6 bg-white/90 backdrop-blur-3xl border border-white/40 rounded-[3rem] shadow-[0_40px_100px_rgba(0,0,0,0.2)] z-[2000] max-h-[500px] overflow-hidden flex flex-col"
              >
                <div className="px-10 py-6 bg-gray-50/50 border-b border-gray-100/50 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                    <p className="text-[10px] font-black text-gray-500 uppercase tracking-[0.25em]">
                      Live Market Intelligence
                    </p>
                  </div>
                  <span className="text-[10px] font-black text-blue-600 bg-blue-50 px-3 py-1 rounded-full uppercase tracking-wider">{liveResults.length} Signals</span>
                </div>
                <div className="overflow-y-auto no-scrollbar p-4 space-y-2">
                  {liveResults.map((lead) => (
                    <motion.button
                      key={lead.id}
                      whileHover={{ x: 4, backgroundColor: 'rgba(255, 255, 255, 1)' }}
                      onClick={() => {
                        setHasSearched(true);
                        onSearch(query, location, lead.id, false);
                        setShowResults(false);
                      }}
                      className="w-full flex items-center gap-6 px-6 py-5 hover:bg-white rounded-[2rem] transition-all text-left group border border-transparent hover:border-gray-100 hover:shadow-xl"
                    >
                      <div className="w-16 h-16 rounded-[1.25rem] bg-gradient-to-br from-blue-50 to-blue-100/50 flex items-center justify-center text-blue-600 font-black text-xl shadow-inner group-hover:scale-105 transition-transform duration-500">
                        {(lead.buyer_name || 'A')[0].toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1.5">
                          <p className="text-base font-black text-gray-900 truncate uppercase italic tracking-tight">{lead.buyer_name || 'Anonymous'}</p>
                          {lead.is_contact_verified === 1 && (
                            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-green-50 text-[9px] font-black text-green-600 rounded-full uppercase tracking-widest border border-green-100/50">
                              <Shield size={10} />
                              Verified
                            </div>
                          )}
                        </div>
                        <p className="text-sm text-gray-500 truncate font-bold leading-relaxed opacity-70 group-hover:opacity-100 transition-opacity italic">
                          "{lead.buyer_request_snippet}"
                        </p>
                      </div>
                      <div className="w-12 h-12 rounded-2xl bg-gray-50 flex items-center justify-center text-gray-300 group-hover:bg-blue-600 group-hover:text-white group-hover:shadow-lg group-hover:shadow-blue-600/20 transition-all duration-300">
                        <ChevronRight size={20} />
                      </div>
                    </motion.button>
                  ))}
                </div>
                <button 
                  onClick={handleSubmit}
                  className="p-6 bg-blue-600 text-white text-xs font-black uppercase tracking-[0.3em] hover:bg-blue-700 transition-colors flex items-center justify-center gap-3 group"
                >
                  <Activity size={18} className="animate-pulse" />
                  View All Signals
                  <ArrowRight size={18} className="group-hover:translate-x-2 transition-transform" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
      
      {/* Stats and Live Feed - Visible by default */}
      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="space-y-10"
      >
        {/* Stats Grid */}
        <SummaryCards stats={stats} />

        {/* Live Feed Section */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h2 className="text-2xl font-black text-gray-900 tracking-tight italic uppercase flex items-center gap-3">
                <Activity size={24} className="text-blue-600" />
                Live Discovery Feed
              </h2>
              <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">
                {hasSearched ? `Real-time signals for "${query}"` : 'Global real-time market signals'}
              </p>
            </div>
            <div className="flex items-center gap-2 text-[10px] font-black text-green-600 bg-green-50 px-4 py-2 rounded-xl border border-green-100 uppercase tracking-widest">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              Monitoring Live
            </div>
          </div>
          <div className="h-[600px] rounded-[2.5rem] overflow-hidden border border-gray-100 shadow-xl bg-white">
            <LiveFeed leads={filteredLeads} />
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default Radar;