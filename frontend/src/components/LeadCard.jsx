import React from 'react';
import { Phone, MessageSquare, Bookmark, ExternalLink, MapPin, Clock, Flame, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';

const LeadCard = ({ lead, onSave, onStatusUpdate, onClick, isSavedView = false }) => {
  const timeAgo = (date) => {
    const seconds = Math.floor((new Date() - new Date(date)) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " years ago";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " months ago";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " minutes ago";
    return Math.floor(seconds) + " seconds ago";
  };

  const getIntentColor = (score) => {
    if (score >= 0.8) return 'text-red-500 bg-red-500/10 border-red-500/20';
    if (score >= 0.5) return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
    return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
  };

  const getIntentLabel = (score) => {
    if (score >= 0.8) return 'High';
    if (score >= 0.5) return 'Medium';
    return 'Low';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={() => onClick(lead)}
      className="bg-[#111] border border-white/5 rounded-xl overflow-hidden hover:border-white/10 transition-all group cursor-pointer"
    >
      <div className="p-5">
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1">
            <h3 className="text-white font-medium text-lg leading-snug group-hover:text-blue-400 transition-colors">
              "{lead.buyer_request_snippet}"
            </h3>
            <div className="flex flex-wrap gap-2 mt-3">
              <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider border ${getIntentColor(lead.intent_score)}`}>
                <Flame size={12} className={lead.intent_score >= 0.8 ? 'animate-pulse' : ''} />
                Intent: {getIntentLabel(lead.intent_score)}
              </span>
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider border border-white/10 text-white/60 bg-white/5">
                <ShieldCheck size={12} />
                {lead.source_platform}
              </span>
            </div>
          </div>
          <button 
            onClick={() => onSave(lead.id)}
            className={`p-2 rounded-lg border transition-all ${lead.is_saved ? 'bg-blue-500/20 border-blue-500/50 text-blue-400' : 'bg-white/5 border-white/10 text-white/40 hover:text-white/60 hover:border-white/20'}`}
          >
            <Bookmark size={18} fill={lead.is_saved ? 'currentColor' : 'none'} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4 py-4 border-y border-white/5 my-4">
          <div className="flex items-center gap-2 text-white/40 text-sm">
            <Clock size={14} />
            <span>{timeAgo(lead.created_at)}</span>
          </div>
          <div className="flex items-center gap-2 text-white/40 text-sm">
            <MapPin size={14} />
            <span>{lead.location_raw || 'Kenya'}</span>
          </div>
        </div>

        {lead.contact_phone && (
          <div className="mb-4 flex items-center gap-2 text-white/80 font-mono text-sm">
            <Phone size={14} className="text-green-500" />
            {lead.contact_phone}
          </div>
        )}

        <div className="flex gap-2">
          <button 
            onClick={(e) => {
              e.stopPropagation();
              onClick(lead);
            }}
            className="flex-1 flex items-center justify-center gap-2 bg-white/5 border border-white/10 text-white font-bold py-2.5 rounded-lg hover:bg-white/10 transition-colors text-sm"
          >
            Details
          </button>
          {lead.contact_phone ? (
            <a 
              href={`tel:${lead.contact_phone}`}
              className="flex-1 flex items-center justify-center gap-2 bg-white text-black font-bold py-2.5 rounded-lg hover:bg-white/90 transition-colors text-sm"
            >
              <Phone size={16} />
              Call
            </a>
          ) : (
             <a 
              href={lead.post_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-2 bg-white text-black font-bold py-2.5 rounded-lg hover:bg-white/90 transition-colors text-sm"
            >
              <ExternalLink size={16} />
              View Post
            </a>
          )}
          
          <button 
            className="flex-1 flex items-center justify-center gap-2 bg-white/5 border border-white/10 text-white font-bold py-2.5 rounded-lg hover:bg-white/10 transition-colors text-sm"
            onClick={() => {/* Open Message Modal */}}
          >
            <MessageSquare size={16} />
            Message
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default LeadCard;
