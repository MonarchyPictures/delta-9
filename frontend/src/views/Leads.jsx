import getApiUrl from '../config';
import React, { useState, useEffect } from 'react';
import { Search, MapPin, Filter, Database } from 'lucide-react';
import LeadCard from '../components/LeadCard';

const Leads = () => {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('Nairobi');

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const apiUrl = getApiUrl();
      const res = await fetch(`${apiUrl}/leads?location=${encodeURIComponent(location)}&query=${encodeURIComponent(query)}`);
      if (res.ok) {
        const data = await res.json();
        setLeads(data);
      }
    } catch (err) {
      console.error("Fetch leads failed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
  fetchLeads();
  const interval = setInterval(() => fetchLeads(true), 10000); // 4. Auto-refresh polling
  return () => clearInterval(interval);
  }, [location, query]);

  return (
    <div className="flex-1 bg-black p-4 md:p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h1 className="text-4xl font-black text-white italic tracking-tighter">LIVE LEADS</h1>
          <div className="flex gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
              <input 
                type="text" 
                placeholder="Filter by intent..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchLeads()}
                className="bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <select 
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:outline-none"
            >
              <option value="Nairobi">Nairobi</option>
              <option value="Kenya">All Kenya</option>
            </select>
          </div>
        </div>

        {loading && leads.length === 0 ? (
          <div className="text-center py-20 text-white/40 font-bold uppercase tracking-widest animate-pulse">Syncing with Market Nodes...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {leads.map((lead) => (
              <LeadCard key={lead.id} lead={lead} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Leads;