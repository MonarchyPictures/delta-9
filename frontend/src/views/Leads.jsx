import React, { useState, useEffect } from 'react';
import LeadCard from '../components/LeadCard';
import LeadTable from '../components/LeadTable';
import { LeadSkeleton, EmptyState, ErrorState } from '../components/UXStates';
import { Filter, Download, Zap, ShieldCheck, Search, SlidersHorizontal, ChevronRight, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const Leads = ({ initialQuery = '', initialLocation = 'Kenya', selectedLeadId = null, onLeadModalClose = () => {} }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [leads, setLeads] = useState([]);
  const [page, setPage] = useState(1);
  const [hours, setHours] = useState(2);
  const [readiness, setReadiness] = useState('ACTIVE');
  const [minProb, setMinProb] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [isLive, setIsLive] = useState(true);
  const [verifiedOnly, setVerifiedOnly] = useState(true);
  const [autoOpenId, setAutoOpenId] = useState(null);
  const [showMobileFilters, setShowMobileFilters] = useState(false);

  useEffect(() => {
    const checkAndFetchLead = async () => {
      if (selectedLeadId) {
        // If we already have it in the list, just open it
        const existingLead = leads.find(l => String(l.id) === String(selectedLeadId));
        if (existingLead) {
          setAutoOpenId(selectedLeadId);
          return;
        }

        // Otherwise fetch it
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        try {
          const response = await fetch(`${import.meta.env.VITE_API_URL}/leads/${selectedLeadId}`, {
            signal: controller.signal
          });
          clearTimeout(timeoutId);
          if (response.ok) {
            const lead = await response.json();
            if (!lead || !lead.id) return;

            const processedLead = {
              ...lead,
              time_ago: lead.created_at ? new Date(lead.created_at).toLocaleTimeString() : 'Recently'
            };
            setLeads(prev => {
              if (!Array.isArray(prev)) return [processedLead];
              if (prev.find(l => String(l.id) === String(lead.id))) return prev;
              return [processedLead, ...prev];
            });
            setAutoOpenId(selectedLeadId);
          }
        } catch (err) {
          clearTimeout(timeoutId);
          console.error("Failed to fetch specific lead:", err);
        }
      }
    };
    checkAndFetchLead();
  }, [selectedLeadId]); // Only run when selectedLeadId changes

  const fetchLeads = async (pageNum = 1, isLoadMore = false, isPolling = false) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);
    
    try {
      if (!isLoadMore && !isPolling) setLoading(true);

      const queryParams = new URLSearchParams({
        page: pageNum,
        limit: 10,
        location: initialLocation,
        verified_only: verifiedOnly ? 'true' : 'false',
        smart_match: 'true'
      });

      if (initialQuery) queryParams.append('query', initialQuery);
      if (hours) queryParams.append('hours', hours);
      if (readiness) queryParams.append('readiness', readiness);
      if (minProb) queryParams.append('min_prob', minProb);

      const res = await fetch(`${import.meta.env.VITE_API_URL}/leads/search?${queryParams}`, {
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      
      const data = await res.json();
      
      if (isLoadMore) {
        setLeads(prev => {
          const newLeads = data.results || [];
          const combined = [...prev, ...newLeads];
          // Simple duplicate removal by ID
          return Array.from(new Map(combined.map(item => [item.id, item])).values());
        });
      } else {
        setLeads(data.results || []);
      }
      
      setHasMore((data.results || []).length === 10);
      setError(null);
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') return;
      console.error("Fetch leads error:", err);
      if (!isPolling) setError("Failed to fetch leads. Please check your connection.");
    } finally {
      if (!isPolling) setLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
    const controller = new AbortController();
    let interval;
    
    // Initial fetch
    fetchLeads(1, false, false);
    
    if (isLive) {
      interval = setInterval(() => {
        fetchLeads(1, false, true);
      }, 10000); // Poll every 10s
    }

    return () => {
      controller.abort();
      if (interval) clearInterval(interval);
    };
  }, [hours, readiness, minProb, isLive, verifiedOnly, initialQuery, initialLocation]); // Re-run when filters change

  const loadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchLeads(nextPage, true);
  };

  const FilterSection = () => (
    <div className="space-y-8">
      <div className="space-y-4">
        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Live Control</h3>
        <div className="space-y-2">
          <button 
            onClick={() => setIsLive(!isLive)}
            className={`w-full flex items-center justify-between p-4 rounded-xl border transition-all ${
              isLive 
                ? 'bg-red-50 border-red-100 text-red-600 shadow-sm' 
                : 'bg-white border-gray-100 text-gray-400 hover:border-gray-200'
            }`}
          >
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${isLive ? 'bg-red-100' : 'bg-gray-50'}`}>
                <Zap size={18} className={isLive ? 'animate-pulse' : ''} />
              </div>
              <span className="text-sm font-bold">Real-time Radar</span>
            </div>
            <div className={`w-10 h-5 rounded-full relative transition-colors duration-300 p-1 ${isLive ? 'bg-red-500' : 'bg-gray-200'}`}>
              <motion.div 
                animate={{ x: isLive ? 20 : 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
                className="w-3 h-3 bg-white rounded-full shadow-sm" 
              />
            </div>
          </button>

          <button 
            onClick={() => setVerifiedOnly(!verifiedOnly)}
            className={`w-full flex items-center justify-between p-4 rounded-xl border transition-all ${
              verifiedOnly 
                ? 'bg-amber-50 border-amber-100 text-amber-600 shadow-sm' 
                : 'bg-white border-gray-100 text-gray-400 hover:border-gray-200'
            }`}
          >
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${verifiedOnly ? 'bg-amber-100' : 'bg-gray-50'}`}>
                <ShieldCheck size={18} />
              </div>
              <span className="text-sm font-bold">Verified Signal</span>
            </div>
            <div className={`w-10 h-5 rounded-full relative transition-colors duration-300 p-1 ${verifiedOnly ? 'bg-amber-500' : 'bg-gray-200'}`}>
              <motion.div 
                animate={{ x: verifiedOnly ? 20 : 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
                className="w-3 h-3 bg-white rounded-full shadow-sm" 
              />
            </div>
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Targeting</h3>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest ml-1">Intent Level</label>
            <select 
              value={readiness}
              onChange={(e) => setReadiness(e.target.value)}
              className="w-full bg-white border border-gray-200 text-gray-900 text-base md:text-sm font-bold rounded-xl p-4 focus:border-blue-500 cursor-pointer outline-none transition-all appearance-none shadow-sm"
            >
              <option value="ACTIVE">🔥 High Intent Only</option>
              <option value="HOT">🚀 Immediate Action</option>
              <option value="WARM">⚡ Considering</option>
              <option value="RESEARCHING">🔍 Awareness</option>
              <option value="ALL">🌐 All Signals</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest ml-1">Probability Threshold</label>
            <select 
              value={minProb}
              onChange={(e) => setMinProb(Number(e.target.value))}
              className="w-full bg-white border border-gray-200 text-gray-900 text-base md:text-sm font-bold rounded-xl p-4 focus:border-blue-500 cursor-pointer outline-none transition-all appearance-none shadow-sm"
            >
              <option value={0}>Any Probability</option>
              <option value={70}>70% Confidence+</option>
              <option value={90}>90% Confidence+</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest ml-1">Time Horizon</label>
            <select 
              value={hours}
              onChange={(e) => setHours(Number(e.target.value))}
              className="w-full bg-white border border-gray-200 text-gray-900 text-base md:text-sm font-bold rounded-xl p-4 focus:border-blue-500 cursor-pointer outline-none transition-all appearance-none shadow-sm"
            >
              <option value={2}>Last 120 Minutes</option>
              <option value={24}>Last 24 Hours</option>
              <option value={168}>Last 7 Days</option>
              <option value={0}>Infinite History</option>
            </select>
          </div>
        </div>
      </div>

      <div className="pt-6 border-t border-gray-100">
        <div className="bg-gray-50 rounded-xl p-5 space-y-4 border border-gray-100">
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Active Deployment</p>
          <div className="space-y-2">
            <p className="text-sm font-bold text-gray-900 italic uppercase">
              {initialQuery || 'Global Discovery'}
            </p>
            <div className="flex flex-wrap gap-2">
              <span className="px-2 py-1 bg-white border border-gray-200 rounded-lg text-[10px] font-bold text-gray-500">
                📍 {initialLocation}
              </span>
              <span className="px-2 py-1 bg-blue-50 border border-blue-100 rounded-lg text-[10px] font-bold text-blue-600 animate-pulse">
                AUTO-SYNC
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-full bg-gray-50/50">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:block w-[320px] bg-white border-r border-gray-200 p-8 overflow-y-auto no-scrollbar sticky top-16 h-[calc(100vh-64px)]">
        <FilterSection />
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="p-6 md:p-10 space-y-8 flex-1 overflow-y-auto no-scrollbar">
          {/* Header Area */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 bg-blue-50 rounded-full border border-blue-100">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-blue-600"></span>
                </span>
                <span className="text-[9px] font-bold uppercase tracking-widest text-blue-600">Lead Feed</span>
              </div>
              <h2 className="text-3xl font-bold text-gray-900 tracking-tight italic uppercase">
                {initialQuery ? `Results: ${initialQuery}` : 'Recent Leads'}
              </h2>
              <p className="text-gray-500 text-sm font-medium max-w-lg">
                Discover and connect with potential customers in real-time.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button 
                onClick={() => setShowMobileFilters(true)}
                className="lg:hidden flex-1 bg-white border border-gray-200 text-gray-900 px-5 py-3 rounded-xl shadow-sm hover:border-blue-500 transition-all flex items-center justify-center gap-2"
              >
                <SlidersHorizontal size={18} className="text-blue-600" />
                <span className="text-xs font-bold uppercase tracking-widest">Filters</span>
              </button>
              <button className="flex-1 md:flex-none bg-gray-900 hover:bg-gray-800 text-white px-6 py-3 rounded-xl shadow-lg shadow-gray-900/10 transition-all flex items-center justify-center gap-2 group active:scale-95">
                <Download size={18} className="group-hover:-translate-y-0.5 transition-transform" />
                <span className="text-xs font-bold uppercase tracking-widest">Export Dataset</span>
              </button>
            </div>
          </div>

          {/* Lead List Area */}
          <div className="flex-1">
            {loading && page === 1 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1, 2, 3, 4, 5, 6].map((n) => <LeadSkeleton key={n} />)}
              </div>
            ) : error ? (
              <ErrorState message={error} />
            ) : leads.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="space-y-12">
                {/* Mobile View: Cards */}
                <div className="md:hidden grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {leads.map((lead) => (
                    <LeadCard 
                      key={lead.id} 
                      lead={lead} 
                      autoOpen={autoOpenId === lead.id}
                      onModalClose={() => {
                        setAutoOpenId(null);
                        onLeadModalClose();
                      }}
                    />
                  ))}
                </div>
                
                {/* Desktop View: Table */}
                <div className="hidden md:block bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                  <LeadTable 
                    leads={leads} 
                    autoOpenId={autoOpenId}
                    onModalClose={() => {
                      setAutoOpenId(null);
                      onLeadModalClose();
                    }}
                  />
                </div>

                {hasMore && (
                  <div className="flex justify-center pt-8 pb-16">
                    <button 
                      onClick={loadMore}
                      disabled={loading}
                      className="bg-white border border-gray-200 text-gray-900 hover:border-blue-500 hover:text-blue-600 px-12 py-4 rounded-xl font-bold uppercase tracking-widest text-[10px] transition-all disabled:opacity-50 shadow-sm active:scale-95"
                    >
                      {loading ? 'Loading leads...' : 'Load More Leads'}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Filters Modal */}
      {showMobileFilters && (
        <div className="fixed inset-0 z-[200] lg:hidden">
          <div className="absolute inset-0 bg-gray-900/60 backdrop-blur-sm" onClick={() => setShowMobileFilters(false)} />
          <div className="absolute right-0 top-0 bottom-0 w-full max-w-[340px] bg-white shadow-2xl animate-in slide-in-from-right duration-500 flex flex-col">
            <div className="p-8 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900 uppercase italic">Refine Feed</h2>
              <button onClick={() => setShowMobileFilters(false)} className="p-3 text-gray-400 hover:bg-gray-100 rounded-xl transition-all">
                <X size={22} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-8 no-scrollbar">
              <FilterSection />
            </div>
            <div className="p-8 border-t border-gray-100 bg-gray-50">
              <button 
                onClick={() => setShowMobileFilters(false)}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl font-bold uppercase tracking-widest text-xs shadow-lg shadow-blue-600/20 transition-all active:scale-95"
              >
                Apply Intelligence Filters
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Leads;
