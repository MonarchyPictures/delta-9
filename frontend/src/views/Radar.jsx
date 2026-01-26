import React, { useState, useEffect } from 'react';
import { Search, MapPin, Zap, Flame, Target, ChevronRight, History, Layers, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import LiveFeed from '../components/LiveFeed';

const Radar = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [radius, setRadius] = useState('Anywhere');
  const [category, setCategory] = useState('All');
  const [hotOnly, setHotOnly] = useState(false);
  const [recentSearches, setRecentSearches] = useState(['Tires', 'Tanks', 'Solar Panels', 'Furniture']);
  
  const [liveLeads, setLiveLeads] = useState([]);
  const [isLiveLoading, setIsLiveLoading] = useState(true);

  // Poll for live leads every 10 seconds
  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const fetchLiveLeads = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/leads/search?live=true&limit=15&verified_only=false`, {
          signal: controller.signal
        });
        const data = await res.json();
        if (isMounted) {
          setLiveLeads(data.results || []);
          setIsLiveLoading(false);
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error("Failed to fetch live leads:", err);
          if (isMounted) setIsLiveLoading(false);
        }
      }
    };

    fetchLiveLeads();
    const interval = setInterval(fetchLiveLeads, 10000);

    return () => {
      isMounted = false;
      controller.abort();
      clearInterval(interval);
    };
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    const params = new URLSearchParams();
    params.append('q', query);
    params.append('radius', radius);
    params.append('category', category);
    params.append('hot', hotOnly);
    
    navigate(`/leads?${params.toString()}`);
  };

  const handleRecentSearch = (search) => {
    setQuery(search);
  };

  return (
    <div className="min-h-[calc(100vh-80px)] flex flex-col items-center p-6 bg-black overflow-y-auto">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-2xl text-center mt-12 mb-16"
      >
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="w-12 h-12 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Target className="text-white" size={28} />
          </div>
          <h1 className="text-4xl font-black text-white tracking-tighter italic">DELTA9</h1>
        </div>

        <form onSubmit={handleSearch} className="space-y-4">
          {/* Search Bar */}
          <div className="relative group">
            <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-white/20 group-focus-within:text-blue-500 transition-colors" size={24} />
            <input 
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="What product are you looking to sell?"
              className="w-full bg-[#111] border border-white/10 text-white px-14 py-6 rounded-2xl text-xl font-medium focus:outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 transition-all placeholder:text-white/20"
            />
          </div>

          {/* Filters Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="relative">
              <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" size={18} />
              <select 
                value={radius}
                onChange={(e) => setRadius(e.target.value)}
                className="w-full bg-[#111] border border-white/10 text-white pl-11 pr-4 py-4 rounded-xl focus:outline-none focus:border-blue-500/50 appearance-none cursor-pointer"
              >
                <option>5km</option>
                <option>50km</option>
                <option>500km</option>
                <option>Anywhere</option>
              </select>
            </div>

            <div className="relative">
              <Layers className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" size={18} />
              <select 
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-[#111] border border-white/10 text-white pl-11 pr-4 py-4 rounded-xl focus:outline-none focus:border-blue-500/50 appearance-none cursor-pointer"
              >
                <option>All Categories</option>
                <option>Automotive</option>
                <option>Electronics</option>
                <option>Home & Garden</option>
                <option>Industrial</option>
              </select>
            </div>

            <button
              type="button"
              onClick={() => setHotOnly(!hotOnly)}
              className={`flex items-center justify-between px-4 py-4 rounded-xl border transition-all ${
                hotOnly 
                ? 'bg-red-500/10 border-red-500/50 text-red-500' 
                : 'bg-[#111] border-white/10 text-white/60 hover:border-white/20'
              }`}
            >
              <div className="flex items-center gap-2">
                <Flame size={18} className={hotOnly ? 'animate-pulse' : ''} />
                <span className="font-bold text-sm uppercase tracking-wider">Hot Leads</span>
              </div>
              <div className={`w-10 h-5 rounded-full relative transition-colors ${hotOnly ? 'bg-red-500' : 'bg-white/10'}`}>
                <div className={`absolute top-1 w-3 h-3 rounded-full bg-white transition-all ${hotOnly ? 'right-1' : 'left-1'}`} />
              </div>
            </button>
          </div>

          <button 
            type="submit"
            className="w-full bg-white text-black font-black text-xl py-6 rounded-2xl hover:bg-white/90 transition-all active:scale-[0.98] shadow-xl shadow-white/5 mt-4"
          >
            Search Leads
          </button>
        </form>

        {/* Recent Searches */}
        <div className="mt-12">
          <div className="flex items-center justify-center gap-2 text-white/30 mb-4">
            <History size={16} />
            <span className="text-sm font-bold uppercase tracking-widest">Recent Searches</span>
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            {recentSearches.map((search) => (
              <button
                key={search}
                onClick={() => handleRecentSearch(search)}
                className="px-4 py-2 bg-white/5 border border-white/10 rounded-full text-white/60 text-sm hover:bg-white/10 hover:text-white transition-all"
              >
                {search}
              </button>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Live Discovery Feed */}
      <div className="w-full max-w-2xl pb-24">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Zap size={18} className="text-blue-500 animate-pulse" />
            <h2 className="text-xl font-bold text-white">Live Discovery Feed</h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-white/40 text-[10px] font-bold uppercase tracking-widest">{liveLeads.length} Active Signals</span>
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
          </div>
        </div>
        
        <div className="h-[500px] rounded-2xl overflow-hidden border border-white/5">
          {isLiveLoading ? (
            <div className="w-full h-full flex flex-col items-center justify-center bg-[#0a0a0a]">
              <Loader2 size={32} className="text-blue-500 animate-spin mb-4" />
              <p className="text-white/20 text-xs font-bold uppercase tracking-widest">Patrolling Platforms...</p>
            </div>
          ) : (
            <LiveFeed leads={liveLeads} />
          )}
        </div>
      </div>
    </div>
  );
};

export default Radar;