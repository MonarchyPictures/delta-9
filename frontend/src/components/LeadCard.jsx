import React from 'react';
import { Phone, Bookmark, ExternalLink, MapPin, Clock, Flame, ShieldCheck, Mail, MessageCircle, User, Trash2 } from 'lucide-react';
import { motion } from 'framer-motion';

const LeadCard = ({ lead, onSave, onDelete, onClick }) => {
  const timeAgo = (date) => {
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

  const getWhatsAppLink = (phone, name, snippet, location, whatsappData) => {
    const targetPhone = (whatsappData?.contact || phone);
    if (!targetPhone) return null;
    
    const cleanPhone = targetPhone.replace(/\D/g, '');
    const defaultMsg = `Hi ${name || 'there'}, I saw your post looking for "${snippet}" in ${location || 'Nairobi'}. I have this available and can deliver today. Can I share price and details?`;
    const message = encodeURIComponent(whatsappData?.message_hint || defaultMsg);
    
    return `https://wa.me/${cleanPhone}?text=${message}`;
  };

  const hasWhatsApp = !!(lead.contact_phone || (lead.whatsapp_ready_data && lead.whatsapp_ready_data.contact));
  const whatsappLink = getWhatsAppLink(lead.contact_phone, lead.buyer_name, lead.buyer_request_snippet, lead.location_raw, lead.whatsapp_ready_data);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={() => onClick && onClick(lead)}
      className="bg-[#0A0A0A] border border-white/5 rounded-2xl overflow-hidden hover:border-white/10 transition-all group cursor-pointer relative"
    >
      {/* Proof of Life Badge */}
      {lead.source_url && (
        <div className="absolute top-4 right-4 flex items-center gap-1.5 bg-blue-600/10 border border-blue-500/20 px-2 py-1 rounded-md z-10">
          <span className="flex h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse"></span>
          <span className="text-[9px] font-black text-blue-400 uppercase tracking-widest">LIVE</span>
        </div>
      )}
      <div className="p-5">
        {/* Top Badges */}
        <div className="flex justify-between items-center mb-4">
          <div className="flex gap-2">
            <span className={`px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border ${getStatusColor(lead.status)}`}>
              {lead.status || 'NEW'}
            </span>
            {(lead.is_hot_lead === 1 || lead.intent_score >= 0.8) && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-red-500/30 bg-red-500/10 text-red-500 flex items-center gap-1">
                <Flame size={10} className="animate-pulse" />
                {lead.is_hot_lead === 1 ? 'HOT LEAD' : 'Buying Now'}
              </span>
            )}
          </div>
          <span className="text-[10px] font-bold text-white/40 uppercase tracking-widest flex items-center gap-1">
            <Clock size={10} />
            {timeAgo(lead.created_at)}
          </span>
        </div>

        {/* Buyer Intent Text (Bold, First) */}
        <h3 className="text-white font-black text-xl leading-tight group-hover:text-blue-400 transition-colors mb-4 italic">
          "{lead.buyer_request_snippet}"
        </h3>

        {/* Location + Distance */}
        <div className="flex items-center gap-4 mb-4">
          <div className="flex items-center gap-1.5 text-white/60 text-xs font-bold">
            <MapPin size={14} className="text-blue-500" />
            <span>{lead.location_raw || 'Kenya'}</span>
            {lead.radius_km > 0 && (
              <span className="text-white/30 ml-1">({lead.radius_km}km)</span>
            )}
          </div>
          <div className="flex items-center gap-1.5 text-white/60 text-xs font-bold">
            <ShieldCheck size={14} className="text-green-500" />
            <span>{lead.source_platform}</span>
          </div>
        </div>

        {/* Buyer Info */}
        <div className="flex items-center gap-2 mb-6 p-2.5 bg-white/5 rounded-xl border border-white/5">
          <div className="w-8 h-8 rounded-full bg-blue-600/20 flex items-center justify-center text-blue-400 border border-blue-500/20">
            <User size={16} />
          </div>
          <div className="flex-1">
            <p className="text-[10px] font-black text-white/40 uppercase tracking-widest leading-none mb-1">Buyer Profile</p>
            <p className="text-xs font-bold text-white leading-none">{lead.buyer_name || 'Anonymous User'}</p>
          </div>
        </div>

        {/* Primary Action */}
        {hasWhatsApp ? (
          <a
            href={whatsappLink}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => {
              e.stopPropagation();
              onSave && onSave(lead.id);
            }}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-black text-xs py-4 rounded-xl flex items-center justify-center gap-2 uppercase tracking-widest transition-all active:scale-95 shadow-lg shadow-green-600/20"
          >
            <MessageCircle size={16} />
            Instant WhatsApp Pitch
          </a>
        ) : (
          <div className="flex flex-col gap-2">
            <button
              disabled
              className="w-full bg-white/5 text-white/20 font-black text-xs py-4 rounded-xl flex items-center justify-center gap-2 uppercase tracking-widest cursor-not-allowed border border-white/5"
            >
              <MessageCircle size={16} />
              WhatsApp Not Available
            </button>
            <p className="text-center text-[10px] font-bold text-white/40 uppercase tracking-[0.2em]">View Profile to Find Contacts</p>
          </div>
        )}

        {/* Secondary Actions Overlay */}
        <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between">
          <div className="flex gap-2">
            <button 
              onClick={(e) => { e.stopPropagation(); onSave && onSave(lead.id); }}
              className="p-2 hover:bg-white/10 rounded-lg text-white/40 hover:text-white transition-colors"
              title="Save for Later"
            >
              <Bookmark size={18} fill={lead.is_saved ? "currentColor" : "none"} />
            </button>
            <button 
              onClick={(e) => { e.stopPropagation(); onDelete && onDelete(lead.id); }}
              className="p-2 hover:bg-red-500/20 rounded-lg text-white/20 hover:text-red-500 transition-colors"
              title="Hide Lead"
            >
              <Trash2 size={18} />
            </button>
          </div>
          
          <button className="text-[10px] font-black text-blue-600 uppercase tracking-widest hover:text-blue-500 transition-colors flex items-center gap-1 group/btn">
            Full Intelligence <ExternalLink size={12} className="group-hover/btn:translate-x-0.5 group-hover/btn:-translate-y-0.5 transition-transform" />
          </button>
        </div>
        {/* Proof of Life Metadata Footer */}
        {lead.source_url && (
          <div className="mt-4 pt-4 border-t border-white/5 flex flex-wrap gap-4 items-center justify-between text-[10px] font-medium text-white/30 uppercase tracking-widest">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <ExternalLink size={10} className="text-blue-500" />
                Source: <span className="text-white/60 truncate max-w-[150px]">{lead.source_url}</span>
              </span>
              <span className="flex items-center gap-1">
                <Clock size={10} />
                Fetched: <span className="text-white/60">{lead.request_timestamp ? new Date(lead.request_timestamp).toLocaleTimeString() : 'N/A'}</span>
              </span>
            </div>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                Status: <span className={lead.http_status === 200 ? "text-green-500" : "text-red-500"}>{lead.http_status || 200}</span>
              </span>
              <span className="flex items-center gap-1">
                Latency: <span className="text-white/60">{lead.latency_ms || 0}ms</span>
              </span>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default LeadCard;
