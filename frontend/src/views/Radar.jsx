import React, { useState, useEffect } from 'react';
import { Flame } from 'lucide-react';
import { motion } from 'framer-motion';
import LiveFeed from '../components/LiveFeed';

const Radar = () => {
  const [liveLeads, setLiveLeads] = useState([]);
  const [isLiveLoading, setIsLiveLoading] = useState(true);

  // Poll for live leads every 10 seconds
  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const fetchLiveLeads = async () => {
      const requestController = new AbortController();
      const timeoutId = setTimeout(() => requestController.abort(), 30000);

      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
        const res = await fetch(`${apiUrl}/leads/search?live=true&limit=15&verified_only=false`, {
          signal: requestController.signal
        });
        
        clearTimeout(timeoutId);
        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            setLiveLeads(data.results || []);
            setIsLiveLoading(false);
          }
        }
      } catch (err) {
        clearTimeout(timeoutId);
        if (err.name === 'AbortError' || !isMounted) return;
        console.error("Failed to fetch live leads:", err);
        if (isMounted) setIsLiveLoading(false);
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

  return (
    <div className="min-h-[calc(100vh-80px)] flex flex-col items-center p-6 bg-black overflow-y-auto">
      {/* Page Title & Status */}
      <div className="w-full max-w-6xl mb-6 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-2">
            <Flame className="w-8 h-8 text-orange-500 fill-orange-500" />
            Live Intelligence Stream
          </h1>
          <p className="text-gray-400">Real-time signals captured from social platforms and the web.</p>
        </div>
        <div className="flex items-center gap-2 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-medium text-emerald-500 uppercase tracking-wider">Patrolling Platforms</span>
        </div>
      </div>

      {/* Live Feed - Full Width */}
      <div className="w-full max-w-6xl">
        <LiveFeed leads={liveLeads} isLoading={isLiveLoading} />
      </div>
    </div>
  );
};

export default Radar;