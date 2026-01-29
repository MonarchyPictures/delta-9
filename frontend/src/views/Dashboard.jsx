import React, { useState, useEffect } from 'react';
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

  const fetchLeads = async (searchQuery, isPolling = false) => {
    if (!isPolling) setLoading(true);
    setErrorMessage(''); // Clear previous error
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      
      if (!isPolling) {
        setLeads([]);
        setHasSearched(true);
        
        // ABSOLUTE RULE: Real-time discovery with no-store cache
        const searchRes = await fetch(`${apiUrl}/search`, {
          method: 'POST',
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
          const errorData = await searchRes.json();
          throw new Error(errorData.detail || 'ERROR: No live sources returned data.');
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
        headers: {
          'X-API-Key': apiKey
        },
        cache: 'no-store' // ENFORCED: No cached data
      });

      const data = await res.json();
      setLeads(data);
    } catch (err) {
      console.error("Discovery error:", err);
      setErrorMessage(err.message);
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
              {errorMessage ? (
                <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-8 text-center">
                  <p className="text-red-500 font-black uppercase tracking-widest text-sm mb-2">PROD_STRICT PIPELINE FAILED</p>
                  <p className="text-white font-bold text-lg">{errorMessage}</p>
                  <p className="text-white/40 text-xs mt-4 uppercase tracking-tighter">Only independently verified outbound signals are permitted in production.</p>
                </div>
              ) : leads.length > 0 ? leads.map((lead) => (
                <LeadCard key={lead.id} lead={lead} onClick={() => navigate('/leads')} />
              )) : null}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Dashboard;