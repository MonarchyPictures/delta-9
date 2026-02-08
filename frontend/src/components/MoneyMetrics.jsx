import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import getApiUrl, { getApiKey } from '../config';

const MoneyMetrics = () => {
  const [stats, setStats] = useState({
    active_listings_24h: 0,
    urgent_sellers: 0,
    whatsapp_taps_today: 0,
    high_intent_matches: 0
  });

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
        console.error("Failed to fetch money metrics:", err);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Every 30s for freshness
    return () => clearInterval(interval);
  }, []);

  const metrics = [
    { label: 'ACTIVE VEHICLES (24H)', value: stats.active_listings_24h, icon: '🔥', color: 'text-orange-500', bg: 'bg-orange-500/5' },
    { label: 'URGENT SELLERS', value: stats.urgent_sellers, icon: '⚡', color: 'text-yellow-500', bg: 'bg-yellow-500/5' },
    { label: 'WHATSAPP TAPS', value: stats.whatsapp_taps_today, icon: '💬', color: 'text-green-500', bg: 'bg-green-500/5' },
    { label: 'MATCHES > 0.8', value: stats.high_intent_matches, icon: '🎯', color: 'text-blue-500', bg: 'bg-blue-500/5' }
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
      {metrics.map((m, i) => (
        <motion.div
          key={m.label}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.05 }}
          className={`${m.bg} border border-white/5 p-5 rounded-3xl flex flex-col items-start relative overflow-hidden group hover:border-white/10 transition-all`}
        >
          <div className="flex items-center justify-between w-full mb-2">
            <span className="text-2xl">{m.icon}</span>
            <div className={`h-1.5 w-1.5 rounded-full ${m.color.replace('text', 'bg')} animate-pulse`}></div>
          </div>
          <span className="text-3xl font-black text-white mb-1 tabular-nums">{m.value}</span>
          <span className="text-[9px] font-black text-white/30 uppercase tracking-[0.2em] leading-tight">
            {m.label}
          </span>
          <div className="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition-opacity">
            <span className="text-6xl grayscale">{m.icon}</span>
          </div>
        </motion.div>
      ))}
    </div>
  );
};

export default MoneyMetrics;
