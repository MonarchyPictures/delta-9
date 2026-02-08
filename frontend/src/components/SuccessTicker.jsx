import React, { useState, useEffect } from 'react';
import { Activity, Zap, MessageCircle, TrendingUp } from 'lucide-react';
import getApiUrl, { getApiKey } from '../config';

const SuccessTicker = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const apiUrl = getApiUrl();
        const apiKey = getApiKey();
        const res = await fetch(`${apiUrl}/success/stats`, {
          headers: { 'X-API-Key': apiKey }
        });
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        }
      } catch (err) {
        console.error("Failed to fetch success stats:", err);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  if (!stats) return null;

  return (
    <div className="w-full bg-blue-600/10 border-y border-blue-500/20 py-2 px-4 flex items-center justify-center gap-8 overflow-hidden whitespace-nowrap">
      <div className="flex items-center gap-2">
        <Activity size={14} className="text-blue-500 animate-pulse" />
        <span className="text-[10px] font-black text-white/60 uppercase tracking-widest">
          Market Pulse:
        </span>
      </div>
      
      <div className="flex items-center gap-2">
        <span className="text-lg">🔥</span>
        <span className="text-[10px] font-black text-white uppercase tracking-widest">
          {stats.active_listings_24h} ACTIVE VEHICLE LISTINGS (24H)
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-lg">⚡</span>
        <span className="text-[10px] font-black text-white uppercase tracking-widest">
          {stats.urgent_sellers} URGENT SELLERS
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-lg">💬</span>
        <span className="text-[10px] font-black text-white uppercase tracking-widest">
          {stats.whatsapp_taps_today} WHATSAPP TAPS
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-lg">🎯</span>
        <span className="text-[10px] font-black text-blue-500 uppercase tracking-widest">
          {stats.high_intent_matches} MATCHES ABOVE 0.8
        </span>
      </div>
    </div>
  );
};

export default SuccessTicker;
