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
    if (!phone && (!whatsappData || !whatsappData.contact)) return null;
    
    const targetPhone = (whatsappData?.contact || phone).replace(/\D/g, '');
    const defaultMsg = `Hi ${name || 'there'}, I saw your post looking for "${snippet}" in ${location || 'Nairobi'}. I have this available and can deliver today. Can I share price and details?`;
    const message = encodeURIComponent(whatsappData?.message_hint || defaultMsg);
    
    return `https://wa.me/${targetPhone}?text=${message}`;
  };

  const whatsappLink = getWhatsAppLink(lead.contact_phone, lead.buyer_name, lead.buyer_request_snippet, lead.location_raw, lead.whatsapp_ready_data);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={() => onClick(lead)}
      className="bg-[#0A0A0A] border border-white/5 rounded-2xl overflow-hidden hover:border-white/10 transition-all group cursor-pointer relative"
    >
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
            {lead.distance_km && (
              <span className="text-white/30 ml-1">({lead.distance_km}km)</span>
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
          {lead.is_contact_verified === 1 && (
            <span className="px-2 py-0.5 bg-green-500/10 text-green-500 text-[8px] font-black uppercase tracking-widest rounded-md border border-green-500/20">
              Verified
            </span>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          {whatsappLink ? (
            <a 
              href={whatsappLink}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="flex-1 flex items-center justify-center gap-2 bg-green-600 text-white font-black uppercase tracking-widest text-[10px] py-3 rounded-xl hover:bg-green-700 transition-all active:scale-95 shadow-lg shadow-green-600/20"
            >
              <MessageCircle size={16} />
              WhatsApp
            </a>
          ) : lead.contact_email ? (
            <a 
              href={`mailto:${lead.contact_email}`}
              onClick={(e) => e.stopPropagation()}
              className="flex-1 flex items-center justify-center gap-2 bg-blue-600 text-white font-black uppercase tracking-widest text-[10px] py-3 rounded-xl hover:bg-blue-700 transition-all active:scale-95 shadow-lg shadow-blue-600/20"
            >
              <Mail size={16} />
              Email
            </a>
          ) : (
            <a 
              href={lead.post_link}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="flex-1 flex items-center justify-center gap-2 bg-white/5 border border-white/10 text-white/40 font-black uppercase tracking-widest text-[10px] py-3 rounded-xl hover:bg-white/10 transition-all"
            >
              WhatsApp Unavailable
            </a>
          )}
          
          <a 
            href={lead.post_link}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="w-12 flex items-center justify-center bg-white/5 border border-white/10 text-white hover:text-blue-400 py-3 rounded-xl hover:bg-white/10 transition-all"
            title="View Source"
          >
            <ExternalLink size={18} />
          </a>

          <button 
            onClick={(e) => {
              e.stopPropagation();
              onSave(lead.id);
            }}
            className={`w-12 flex items-center justify-center rounded-xl border transition-all ${lead.is_saved ? 'bg-blue-500/20 border-blue-500/50 text-blue-400' : 'bg-white/5 border-white/10 text-white/40 hover:text-white/60 hover:border-white/20'}`}
            title="Save Lead"
          >
            <Bookmark size={18} fill={lead.is_saved ? 'currentColor' : 'none'} />
          </button>

          {onDelete && (
            <button 
              onClick={(e) => {
                e.stopPropagation();
                onDelete(lead.id);
              }}
              className="w-12 flex items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white/40 hover:text-red-500 hover:border-red-500/30 transition-all"
              title="Discard Lead"
            >
              <Trash2 size={18} />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default LeadCard;
