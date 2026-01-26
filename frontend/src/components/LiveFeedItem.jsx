import React from 'react';
import { motion } from 'framer-motion';
import { MapPin, ArrowRight, Zap, Search } from 'lucide-react';

const LiveFeedItem = ({ lead, isNew }) => {
  const handleEngage = async (e) => {
    e.stopPropagation();
    try {
      await fetch(`${import.meta.env.VITE_API_URL}/outreach/contact/${lead.id}`, {
        method: 'POST',
      });
    } catch (err) {
      console.error("Failed to track engagement", err);
    }
    window.open(lead.post_link, '_blank');
  };

  return (
    <motion.div
      initial={isNew ? { opacity: 0, x: -20 } : false}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className={`relative px-6 py-5 hover:bg-gray-50 transition-all group cursor-pointer border-l-2 ${
        isNew ? 'bg-blue-50/50 border-blue-600' : 'bg-transparent border-transparent'
      }`}
      onClick={() => window.open(lead.post_link, '_blank')}
    >
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-3">
          <div className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-widest flex items-center gap-1.5 border ${
            lead.intent_score > 0.8 
              ? 'bg-red-50 text-red-600 border-red-100' 
              : 'bg-blue-50 text-blue-600 border-blue-100'
          }`}>
            {lead.intent_score > 0.8 ? <Zap size={10} className="fill-red-500" /> : <Search size={10} />}
            {lead.intent_score > 0.8 ? 'High Intent' : 'Discovery'}
          </div>
          <span className="text-[9px] text-gray-400 font-bold uppercase tracking-[0.1em]">{lead.source_platform}</span>
        </div>
        <span className="text-[9px] text-gray-400 font-bold uppercase tracking-widest">{lead.time_ago}</span>
      </div>
      
      <p className="text-sm text-gray-600 font-medium mb-4 leading-relaxed line-clamp-2">
        "{lead.buyer_request_snippet}"
      </p>
      
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-1.5 text-gray-400">
          <MapPin size={12} className="text-blue-600/60" />
          <span className="text-[10px] font-bold uppercase tracking-tight">{lead.location_raw}</span>
        </div>
        <button 
          onClick={handleEngage}
          className="flex items-center gap-1.5 text-[10px] font-bold text-blue-600 uppercase tracking-[0.15em] hover:text-blue-700 transition-colors group/btn"
        >
          Engage 
          <ArrowRight size={14} className="group-hover/btn:translate-x-1 transition-transform" />
        </button>
      </div>
    </motion.div>
  );
};

export default LiveFeedItem;
