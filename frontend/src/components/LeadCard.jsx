import React from 'react';
import {
  Phone,
  Bookmark,
  ExternalLink,
  MapPin,
  Clock,
  Flame,
  ShieldCheck,
  Mail,
  MessageCircle,
  User,
  Trash2,
  Zap,
  Globe,
  Share2
} from 'lucide-react';
import { motion } from 'framer-motion';
import getApiUrl, { getApiKey } from '../config';

const LeadCard = ({ lead, onSave, onDelete, onClick, onStatusChange }) => {
  const timeAgo = (date) => {
    if (!date) return "N/A";
    const seconds = Math.floor((new Date() - new Date(date)) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + "y ago";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + "mo ago";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + "d ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + "h ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + "m ago";
    return Math.floor(seconds) + "s ago";
  };

  const getStatusColor = (status) => {
    const s = status?.toLowerCase() || 'new';
    switch (s) {
      case 'new': return 'text-green-500 bg-green-500/10 border-green-500/20';
      case 'contacted': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      case 'replied': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
      case 'negotiating': return 'text-purple-500 bg-purple-500/10 border-purple-500/20';
      case 'converted': return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20';
      case 'dead': return 'text-red-500 bg-red-500/10 border-red-500/20';
      default: return 'text-gray-500 bg-gray-500/10 border-gray-500/20';
    }
  };

  const hasWhatsApp = !!lead.phone;
  const whatsappLink = lead.whatsapp_link;

  const displayPhone = (phone) => {
    if (!phone) return null;
    // Handle format 2547XXXXXXXX
    if (phone.startsWith('254') && phone.length === 12) {
      return `+254 ${phone.slice(3, 5)} ${phone.slice(5, 8)} ${phone.slice(8)}`;
    }
    return phone;
  };

  const handleContact = async (e) => {
    e.stopPropagation();
    if (hasWhatsApp) {
      window.open(whatsappLink, '_blank');
      onStatusChange && onStatusChange(lead.lead_id, 'contacted');
      
      // Explicitly track the contact/tap on the backend
      try {
        const apiUrl = getApiUrl();
        const apiKey = getApiKey();
        const sessionId = localStorage.getItem('d9_session_id');
        await fetch(`${apiUrl}/outreach/contact/${lead.lead_id}`, {
          method: 'POST',
          headers: { 
            'X-API-Key': apiKey,
            'X-Session-ID': sessionId
          }
        });
      } catch (err) {
        console.error("Failed to track contact:", err);
      }
    } else if (lead.source_url) {
      window.open(lead.source_url, '_blank');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={handleContact}
      className="bg-[#0A0A0A] border border-white/5 rounded-2xl overflow-hidden hover:border-blue-500/50 transition-all group cursor-pointer relative"
    >
      <div className="p-5">
        {/* Top Badges */}
        <div className="flex justify-between items-center mb-4">
          <div className="flex gap-2">
            <select
              value={lead.status || 'new'}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => onStatusChange && onStatusChange(lead.lead_id, e.target.value)}
              className={`px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border bg-transparent focus:outline-none cursor-pointer ${getStatusColor(lead.status)}`}
            >
              <option value="new" className="bg-neutral-900">NEW</option>
              <option value="contacted" className="bg-neutral-900">CONTACTED</option>
              <option value="replied" className="bg-neutral-900">REPLIED</option>
              <option value="negotiating" className="bg-neutral-900">NEGOTIATING</option>
              <option value="converted" className="bg-neutral-900">CONVERTED</option>
              <option value="dead" className="bg-neutral-900">DEAD</option>
            </select>
            {lead.buyer_match_score > 0.4 && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-blue-500/30 bg-blue-500/10 text-blue-500 flex items-center gap-1">
                <Zap size={10} fill="currentColor" className="text-blue-500" />
                {Math.round(lead.buyer_match_score * 100)}% MATCH
              </span>
            )}
            {lead.intent_strength >= 0.85 && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-red-500/30 bg-red-500/10 text-red-500 flex items-center gap-1">
                <Flame size={10} className="animate-pulse" />
                HOT
              </span>
            )}
            {lead.urgency_level === 'high' && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-orange-500/30 bg-orange-500/10 text-orange-500 flex items-center gap-1">
                URGENT
              </span>
            )}
            {lead.phone && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-green-500/30 bg-green-500/10 text-green-500 flex items-center gap-1">
                <ShieldCheck size={10} />
                VERIFIED
              </span>
            )}
            {lead.contact_source === 'inferred' && !lead.phone && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-blue-500/30 bg-blue-500/10 text-blue-500 flex items-center gap-1">
                <ExternalLink size={10} />
                INFERRED
              </span>
            )}
          </div>
          <span className="text-[10px] font-bold text-white/40 uppercase tracking-widest flex items-center gap-1">
            <Clock size={10} />
            {timeAgo(lead.timestamp)}
          </span>
        </div>

        {/* User Info - ENRICHED */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-white font-black text-sm italic">
            {lead.buyer_name?.charAt(0) || 'V'}
          </div>
          <div>
            <div className="text-white font-bold text-sm flex items-center gap-2">
              {lead.buyer_name || 'Verified Market Signal'}
              {lead.phone && <span className="text-green-500"><ShieldCheck size={12} /></span>}
            </div>
            <div className="text-white/40 text-[10px] font-black uppercase tracking-widest">
              {lead.phone ? displayPhone(lead.phone) : 'Contact via Platform'}
            </div>
          </div>
        </div>

        {/* Product + Intent Text - READ */}
        <div className="mb-4">
          <div className="text-blue-500 text-[11px] font-black uppercase tracking-[0.2em] mb-1">{lead.product || 'General Request'}</div>
          <h3 className="text-white font-black text-xl leading-tight group-hover:text-blue-400 transition-colors italic">
            "Looking for {lead.product}{lead.quantity ? ` (${lead.quantity})` : ''}"
          </h3>
          {lead.buyer_request_snippet && (
            <p className="text-white/40 text-xs mt-2 line-clamp-2 italic font-medium leading-relaxed">
              ...{lead.buyer_request_snippet.substring(0, 150)}...
            </p>
          )}
        </div>

        {/* Location + Source */}
        <div className="flex items-center gap-4 mb-6">
          <div className="flex items-center gap-1.5 text-white/60 text-xs font-bold">
            <MapPin size={14} className="text-blue-500" />
            <span>{lead.location || 'Kenya'}</span>
            {lead.distance_km > 0 && (
              <span className="text-white/30 ml-1">({lead.distance_km}km)</span>
            )}
          </div>
          <div className="flex items-center gap-1.5 text-white/40 text-[10px] font-black uppercase tracking-widest">
            <span>{lead.source}</span>
          </div>
          {lead.source_url && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                window.open(lead.source_url, '_blank');
              }}
              className="ml-auto text-blue-500 hover:text-blue-400 text-[10px] font-black uppercase tracking-widest flex items-center gap-1 transition-colors"
            >
              <ExternalLink size={12} />
              SOURCE
            </button>
          )}
        </div>

        {/* Suggested Outreach Section */}
        {lead.outreach_suggestion && (
          <div className="mb-6 p-4 rounded-xl bg-blue-500/5 border border-blue-500/10 relative overflow-hidden group/suggestion">
            <div className="absolute top-0 left-0 w-1 h-full bg-blue-500/20" />
            <div className="text-[10px] font-black text-blue-500 uppercase tracking-widest mb-2 flex items-center gap-1.5">
              <Zap size={10} fill="currentColor" />
              Suggested Outreach
            </div>
            <p className="text-white/80 text-xs italic font-medium leading-relaxed">
              "{lead.outreach_suggestion}"
            </p>
          </div>
        )}

        {/* Primary Action - TAP */}
        {hasWhatsApp ? (
          <button
            className="w-full bg-green-600 group-hover:bg-green-500 text-white font-black text-sm py-4 rounded-xl flex items-center justify-center gap-3 uppercase tracking-widest transition-all active:scale-95 shadow-lg shadow-green-600/20"
          >
            <MessageCircle size={20} fill="white" />
            TAP TO WHATSAPP
          </button>
        ) : lead.source_url ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              window.open(lead.source_url, '_blank');
            }}
            className="w-full bg-blue-600 group-hover:bg-blue-500 text-white font-black text-sm py-4 rounded-xl flex items-center justify-center gap-3 uppercase tracking-widest transition-all active:scale-95 shadow-lg shadow-blue-600/20"
          >
            <ExternalLink size={20} />
            OPEN SOURCE PLATFORM
          </button>
        ) : (
          <div className="flex flex-col gap-2">
            <button
              disabled
              className="w-full bg-white/5 text-white/20 font-black text-xs py-4 rounded-xl flex items-center justify-center gap-2 uppercase tracking-widest cursor-not-allowed border border-white/5"
            >
              <MessageCircle size={16} />
              NO CONTACT LINK
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default LeadCard;
