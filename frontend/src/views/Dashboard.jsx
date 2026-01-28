import React, { useState, useEffect } from 'react';
import { Search, Activity, Target } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import LeadCard from '../components/LeadCard';
import getApiUrl from '../config';

const Dashboard = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const fetchLeads = async (searchQuery, isPolling = false) => {
    if (!isPolling) setLoading(true);
    try {
      const apiUrl = getApiUrl();
      if (!isPolling) {
        setLeads([]);
        setHasSearched(true);
        // Direct DB Ingestion Trigger
        await fetch(`${apiUrl}/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ query: searchQuery, location: 'Nairobi' })
        });
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

      const res = await fetch(`${apiUrl}/leads?query=${encodeURIComponent(searchQuery)}&limit=10`);
      if (res.ok) {
        const data = await res.json();
        setLeads(data);
      }
    } catch (err) {
      console.error("Discovery error:", err);
    } finally {
      if (!isPolling) setLoading(false);
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
            placeholder="Search Nairobi buyer intent (e.g. 'apartments in Westlands')..."
            className="w-full bg-white/5 border border-white/10 text-white text-xl rounded-3xl pl-16 p-6 shadow-2xl outline-none font-bold placeholder:text-white/20 italic"
          />
        </div>
      </div>

      <AnimatePresence>
        {hasSearched && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex-1 overflow-y-auto px-4 pb-12">
            <div className="max-w-4xl mx-auto space-y-4">
              {leads.length > 0 ? leads.map((lead) => (
                <LeadCard key={lead.id} lead={lead} onClick={() => navigate('/leads')} />
              )) : !loading && <p className="text-center text-white/20 font-bold py-20">NO ACTIVE SIGNALS IN NAIROBI NODES</p>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Dashboard;