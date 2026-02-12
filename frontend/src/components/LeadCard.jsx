import React, { useState } from 'react';
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
  Activity,
  Share2,
  Copy,
  Check
} from 'lucide-react';
import { motion } from 'framer-motion';
import getApiUrl, { getApiKey } from '../config';

const LeadCard = ({ lead, onSave, onDelete, onClick, onStatusChange, onTap }) => {
  const [copied, setCopied] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [localOutreach, setLocalOutreach] = useState(lead.outreach_suggestion);

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

  const getMatchCue = (score) => {
    const s = score || 0;
    if (s >= 0.85) return { icon: "🟢", label: "HOT BUYER", color: "text-green-500", border: "border-green-500/30", bg: "bg-green-500/10" };
    if (s >= 0.6) return { icon: "🟡", label: "warm", color: "text-yellow-500", border: "border-yellow-500/30", bg: "bg-yellow-500/10" };
    return { icon: "⚪", label: "ignore", color: "text-white/20", border: "border-white/10", bg: "bg-white/5" };
  };

  const isRecent = lead.timestamp && (new Date() - new Date(lead.timestamp)) < 24 * 60 * 60 * 1000;
  const isHighIntent = lead.intent_score >= 0.8;
  const matchCue = getMatchCue(lead.buyer_match_score);

  const hasWhatsApp = !!lead.whatsapp_link;
  const whatsappLink = lead.whatsapp_url || lead.whatsapp_link;

  const displayPhone = (phone) => {
    if (!phone) return null;
    // Handle format 2547XXXXXXXX
    if (phone.startsWith('254') && phone.length === 12) {
      return `+254 ${phone.slice(3, 5)} ${phone.slice(5, 8)} ${phone.slice(8)}`;
    }
    return phone;
  };

  const handleUnlock = async (e) => {
    e.stopPropagation();
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      const response = await fetch(`${apiUrl}/api/leads/${lead.lead_id}/unlock`, {
        method: 'POST',
        headers: { 
          'X-API-Key': apiKey,
          'Content-Type': 'application/json'
        }
      });

      if (response.status === 402) {
        alert("💰 Insufficient Credits: Please top up your wallet to unlock this Hot Lead (Cost: KES 150).");
        return;
      }

      if (response.ok) {
        alert("✅ Lead Unlocked! You can now access the contact details.");
        if (onStatusChange) onStatusChange(lead.lead_id, lead.status); // Trigger refresh in parent
      }
    } catch (err) {
      console.error("Unlock error:", err);
    }
  };

  const handleContact = async (e) => {
    e.stopPropagation();
    
    // Always prioritize one-click WhatsApp if we have a contact
    if (hasWhatsApp) {
      setIsGenerating(true);
      try {
        const apiUrl = getApiUrl();
        const apiKey = getApiKey();
        
        // Fetch the prefilled WhatsApp URL from the backend
        const response = await fetch(`${apiUrl}/outreach/${lead.lead_id}/whatsapp`, {
          headers: { 'X-API-Key': apiKey }
        });

        if (response.ok) {
          const data = await response.json();
          window.open(data.url, '_blank');
          if (onTap) {
            onTap(lead.lead_id || lead.id);
          } else {
            onStatusChange && onStatusChange(lead.lead_id || lead.id, 'contacted');
          }
        } else {
          // Fallback if the endpoint fails but we have a direct link
          if (whatsappLink) {
            window.open(whatsappLink, '_blank');
            if (onTap) {
              onTap(lead.lead_id || lead.id);
            } else {
              onStatusChange && onStatusChange(lead.lead_id || lead.id, 'contacted');
            }
          }
        }
      } catch (err) {
        console.error("Outreach error:", err);
        // Fallback to direct link on error
        if (whatsappLink) {
          window.open(whatsappLink, '_blank');
          if (onTap) {
            onTap(lead.lead_id || lead.id);
          } else {
            onStatusChange && onStatusChange(lead.lead_id || lead.id, 'contacted');
          }
        }
      } finally {
        setIsGenerating(false);
      }
    } else if (lead.source_url) {
      window.open(lead.source_url, '_blank');
    }
  };

  const handleCopyOutreach = (e) => {
    e.stopPropagation();
    const textToCopy = localOutreach || lead.outreach_suggestion;
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleGenerateOutreach = async (e) => {
    e.stopPropagation();
    setIsGenerating(true);
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      const res = await fetch(`${apiUrl}/outreach/${lead.lead_id}`, {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey
        }
      });
      if (res.ok) {
        const data = await res.json();
        setLocalOutreach(data.message);
      }
    } catch (err) {
      console.error("Outreach generation failed:", err);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      onClick={() => handleContact({ stopPropagation: () => {} })}
      className="bg-[#0A0A0B] border border-white/5 rounded-3xl p-6 relative group hover:border-blue-500/30 transition-all duration-300 shadow-2xl cursor-pointer"
    >
      <div className="relative z-10">
        {/* Header - Tags + Time */}
        <div className="flex justify-between items-start mb-6">
          <div className="flex flex-wrap gap-2">
            {isHighIntent && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-red-500/30 bg-red-500/10 text-red-500 flex items-center gap-1">
                🔥 High intent
              </span>
            )}
            {hasWhatsApp && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-green-500/30 bg-green-500/10 text-green-500 flex items-center gap-1">
                💬 WhatsApp
              </span>
            )}
            {isRecent && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-blue-500/30 bg-blue-500/10 text-blue-500 flex items-center gap-1">
                ⏱ Recent
              </span>
            )}
            {lead.is_verified && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-blue-500/30 bg-blue-500/10 text-blue-500 flex items-center gap-1">
                <ShieldCheck size={10} />
                VERIFIED
              </span>
            )}
            {lead.tap_count > 0 && (
              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-widest border border-blue-500/30 bg-blue-500/10 text-blue-500 flex items-center gap-1">
                <Activity size={10} />
                TAPS: {lead.tap_count}
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
            {lead.buyer_name?.charAt(0) || 'B'}
          </div>
          <div>
            <div className="text-white font-bold text-sm flex items-center gap-2">
              {lead.buyer_name || 'Verified Buyer'}
              {lead.phone && <span className="text-green-500"><ShieldCheck size={12} /></span>}
            </div>
            <div className={`text-white/40 text-[10px] font-black uppercase tracking-widest ${lead.is_hot_lead && !lead.is_unlocked ? 'blur-sm select-none' : ''}`}>
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
              className="ml-auto text-blue-500 hover:text-blue-400 text-[10px] font-black uppercase tracking-widest flex items-center gap-1 transition-colors cursor-pointer"
            >
              <ExternalLink size={12} />
              SOURCE
            </button>
          )}
        </div>

        {/* Suggested Outreach Section */}
        {(localOutreach || lead.outreach_suggestion) && (
          <div className={`mb-6 p-4 rounded-xl bg-blue-500/5 border border-blue-500/10 relative overflow-hidden group/suggestion ${lead.is_hot_lead && !lead.is_unlocked ? 'opacity-50 grayscale pointer-events-none' : ''}`}>
            <div className="absolute top-0 left-0 w-1 h-full bg-blue-500/20" />
            <div className="flex justify-between items-center mb-2">
              <div className="text-[10px] font-black text-blue-500 uppercase tracking-widest flex items-center gap-1.5">
                <Zap size={10} fill="currentColor" />
                AI Outreach Signal
              </div>
              <div className="flex gap-2">
                <button 
                  onClick={handleGenerateOutreach}
                  disabled={isGenerating}
                  className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-widest bg-white/5 text-white/40 border border-white/10 hover:bg-white/10 transition-all disabled:opacity-50 cursor-pointer"
                >
                  <Activity size={10} className={isGenerating ? "animate-spin" : ""} />
                  {isGenerating ? 'GENERATING...' : 'REGENERATE'}
                </button>
                <button 
                  onClick={handleCopyOutreach}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-widest transition-all cursor-pointer ${
                    copied 
                      ? 'bg-green-500/20 text-green-500 border border-green-500/30' 
                      : 'bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20'
                  }`}
                >
                  {copied ? <Check size={10} /> : <Copy size={10} />}
                  {copied ? 'COPIED' : 'COPY'}
                </button>
              </div>
            </div>
            <p className="text-white/80 text-xs italic font-medium leading-relaxed">
              "{localOutreach || lead.outreach_suggestion}"
            </p>
          </div>
        )}

        {/* Primary Actions - TAP + COPY */}
        <div className="flex gap-3">
          {lead.is_hot_lead && !lead.is_unlocked ? (
            <button
              onClick={handleUnlock}
              className="flex-1 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 text-white font-black text-sm py-4 rounded-xl flex items-center justify-center gap-3 uppercase tracking-widest transition-all active:scale-95 shadow-lg shadow-red-600/20 cursor-pointer"
            >
              <Zap size={20} fill="white" className="animate-pulse" />
              Unlock Hot Lead (KES 150)
            </button>
          ) : hasWhatsApp ? (
            <button
              onClick={handleContact}
              disabled={isGenerating}
              className="flex-1 bg-green-600 hover:bg-green-500 text-white font-black text-sm py-4 rounded-xl flex items-center justify-center gap-3 uppercase tracking-widest transition-all active:scale-95 shadow-lg shadow-green-600/20 disabled:opacity-50 cursor-pointer"
            >
              {isGenerating ? <Activity size={20} className="animate-spin" /> : <MessageCircle size={20} fill="white" />}
              {isGenerating ? 'CONNECTING...' : 'TAP TO WHATSAPP'}
            </button>
          ) : lead.source_url ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                window.open(lead.source_url, '_blank');
              }}
              className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-black text-sm py-4 rounded-xl flex items-center justify-center gap-3 uppercase tracking-widest transition-all active:scale-95 shadow-lg shadow-blue-600/20 cursor-pointer"
            >
              <ExternalLink size={20} />
              OPEN SOURCE PLATFORM
            </button>
          ) : (
            <div className="flex-1 flex flex-col gap-2">
              <button
                disabled
                className="w-full bg-white/5 text-white/20 font-black text-xs py-4 rounded-xl flex items-center justify-center gap-2 uppercase tracking-widest cursor-not-allowed border border-white/5"
              >
                <MessageCircle size={16} />
                NO CONTACT LINK
              </button>
            </div>
          )}

          <button
            onClick={handleContact}
            disabled={isGenerating || !hasWhatsApp}
            className={`px-6 py-4 rounded-xl font-black text-sm uppercase tracking-widest transition-all active:scale-95 flex items-center justify-center gap-2 ${
              hasWhatsApp 
                ? 'bg-green-600/20 border border-green-500/30 text-green-500 hover:bg-green-600/30 hover:text-green-400 cursor-pointer' 
                : 'bg-white/5 border border-white/10 text-white/20 cursor-not-allowed'
            }`}
          >
            <MessageCircle size={18} />
            {hasWhatsApp ? '💬 WHATSAPP BUYER' : 'NO CONTACT'}
          </button>

          <button
            onClick={async (e) => {
              e.stopPropagation();
              setIsGenerating(true);
              try {
                const apiUrl = getApiUrl();
                const apiKey = getApiKey();
                const res = await fetch(`${apiUrl}/outreach/${lead.lead_id}`, {
                  method: 'POST',
                  headers: { 'X-API-Key': apiKey }
                });
                if (res.ok) {
                  const data = await res.json();
                  await navigator.clipboard.writeText(data.message);
                  setLocalOutreach(data.message);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }
              } catch (err) {
                console.error("Instant outreach failed:", err);
              } finally {
                setIsGenerating(false);
              }
            }}
            disabled={isGenerating}
            className={`px-6 py-4 rounded-xl border font-black text-sm uppercase tracking-widest transition-all active:scale-95 flex items-center gap-2 ${
              copied 
                ? 'bg-green-500/20 border-green-500 text-green-500' 
                : 'bg-white/5 border-white/10 text-white/60 hover:bg-white/10 hover:text-white'
            }`}
          >
            {copied ? <Check size={18} /> : isGenerating ? <Activity size={18} className="animate-spin" /> : <Mail size={18} />}
            {copied ? 'COPIED' : '📩 COPY OUTREACH'}
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default LeadCard;
