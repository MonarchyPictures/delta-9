import React, { useState, useEffect } from 'react';
import StatusBadge from './StatusBadge';
import { MapPin, Clock, ArrowRight, Share2, User, Phone, Mail, Facebook, Globe, MessageCircle, ShieldCheck, Zap, Info, ExternalLink, MessageSquare, Users, Timer, Sparkles, CheckCircle2, AlertCircle, BarChart3, X, MoreHorizontal, Search } from 'lucide-react';

const SourceIcon = ({ source }) => {
  const s = source?.toLowerCase() || '';
  if (s.includes('facebook')) return <Facebook size={14} className="text-[#1877F2]" />;
  if (s.includes('reddit')) return <MessageCircle size={14} className="text-[#FF4500]" />;
  if (s.includes('tiktok')) return <MessageCircle size={14} className="text-[#EE1D52]" />;
  return <Globe size={14} className="text-[#6B7280]" />;
};

const VerificationBadge = ({ type }) => {
  const badges = {
    verified_contact: { label: 'Verified Contact', color: 'bg-green-50 text-green-600 border-green-100' },
    active_buyer: { label: 'Active Buyer', color: 'bg-blue-50 text-blue-600 border-blue-100' },
    high_intent: { label: 'High Intent', color: 'bg-purple-50 text-purple-600 border-purple-100' }
  };
  const badge = badges[type] || { label: type, color: 'bg-gray-50 text-gray-500 border-gray-100' };
  return (
    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-md border ${badge.color}`}>
      {badge.label}
    </span>
  );
};

const ReadinessBadge = ({ level }) => {
  const configs = {
    'HOT': { label: 'Hot Lead', color: 'bg-red-500 text-white border-red-500', icon: <Zap size={10} className="fill-white" /> },
    'WARM': { label: 'Warm Lead', color: 'bg-amber-500 text-white border-amber-500', icon: <Zap size={10} className="fill-white" /> },
    'RESEARCHING': { label: 'Researching', color: 'bg-gray-500 text-white border-gray-500', icon: <Search size={10} /> }
  };
  const config = configs[level] || configs['RESEARCHING'];
  return (
    <span className={`text-[10px] font-bold px-2 py-1 rounded-md border flex items-center gap-1.5 ${config.color}`}>
      {config.icon}
      {config.label}
    </span>
  );
};

const LeadCard = ({ lead, autoOpen = false, onModalClose = () => {} }) => {
  const [showModal, setShowModal] = useState(false);
  const [timeSince, setTimeSince] = useState('');
  const [isNew, setIsNew] = useState(false);
  
  const whatsappUrl = lead?.contact_phone ? `https://wa.me/${lead.contact_phone.replace(/\D/g, '')}` : null;

  useEffect(() => {
    if (autoOpen) {
      setShowModal(true);
    }
  }, [autoOpen]);

  useEffect(() => {
    if (!showModal && autoOpen) {
      onModalClose();
    }
  }, [showModal, autoOpen, onModalClose]);

  useEffect(() => {
    if (!lead?.created_at) return;
    const updateTimer = () => {
      const created = new Date(lead.created_at);
      const now = new Date();
      const diffMs = now - created;
      const diffMins = Math.floor(diffMs / 60000);
      
      setIsNew(diffMins < 5);
      
      if (diffMins < 1) setTimeSince('Just now');
      else if (diffMins < 60) setTimeSince(`${diffMins}m ago`);
      else if (diffMins < 1440) setTimeSince(`${Math.floor(diffMins / 60)}h ago`);
      else setTimeSince(`${Math.floor(diffMins / 1440)}d ago`);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 60000);
    return () => clearInterval(interval);
  }, [lead?.created_at]);

  const isExpiring = (lead?.optimal_response_window?.toLowerCase().includes('min') || lead?.optimal_response_window?.toLowerCase().includes('asap')) && 
                    (new Date() - new Date(lead?.created_at) > 600000);

  const handleContact = async (e) => {
    e.stopPropagation();
    if (!lead) return;
    try {
      await fetch(`${import.meta.env.VITE_API_URL}/outreach/contact/${lead.id}`, {
        method: 'POST',
      });
    } catch (err) {
      console.error("Failed to mark as contacted", err);
    }
    window.open(lead.post_link, '_blank');
  };

  if (!lead) return null;

  return (
    <>
      <div 
        className={`bg-white p-5 rounded-xl border border-gray-200 group relative flex flex-col gap-4 cursor-pointer hover:border-blue-400 transition-all ${isNew ? 'ring-2 ring-blue-50 border-blue-200' : ''}`}
        onClick={() => setShowModal(true)}
      >
        {/* Header */}
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-2">
            <ReadinessBadge level={lead.readiness_level} />
            <div className="flex items-center gap-1.5 px-2 py-1 bg-gray-50 rounded-md border border-gray-100">
              <SourceIcon source={lead.source_platform} />
              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">{lead.source_platform}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isNew && (
              <span className="flex items-center gap-1 bg-blue-50 text-blue-600 text-[10px] font-bold px-2 py-1 rounded-full">
                <Sparkles size={10} /> NEW
              </span>
            )}
            <button className="p-1.5 text-gray-400 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors">
              <MoreHorizontal size={16} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gray-50 border border-gray-100 flex items-center justify-center overflow-hidden shrink-0">
              <User size={20} className="text-gray-400" />
            </div>
            <div className="min-w-0">
              <h4 className="text-sm font-bold text-gray-900 truncate">{lead.buyer_name || 'Anonymous User'}</h4>
              <div className="flex items-center gap-1 text-gray-500">
                <MapPin size={12} />
                <span className="text-[11px] font-medium truncate">{lead.location_raw}</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-50 border border-gray-100 rounded-lg p-3 relative">
            <p className="text-xs text-gray-600 leading-relaxed line-clamp-2 italic">
              "{lead.buyer_request_snippet}"
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-50 border border-blue-100 rounded-md text-blue-600">
              <Zap size={12} className="fill-current" />
              <span className="text-[10px] font-bold">{lead.deal_probability}% Match</span>
            </div>
            {lead.budget_info && lead.budget_info !== "Negotiable" && (
              <div className="flex items-center gap-1.5 px-2 py-1 bg-green-50 border border-green-100 rounded-md text-green-600">
                <span className="text-[10px] font-bold">{lead.budget_info}</span>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-gray-100 flex items-center justify-between mt-auto">
          <div className="flex items-center gap-1.5 text-gray-400">
            <Timer size={12} />
            <span className="text-[10px] font-medium">{timeSince}</span>
          </div>
          <button 
            onClick={handleContact}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-1.5 px-4 rounded-lg text-xs flex items-center gap-2 transition-all active:scale-95 shadow-sm shadow-blue-600/10"
          >
            Engage
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Detail Modal */}
      {showModal && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" onClick={() => setShowModal(false)} />
          <div className="relative bg-white w-full max-w-2xl max-h-[90vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in duration-200">
            {/* Header */}
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600">
                  <ShieldCheck size={28} />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Lead Details</h2>
                  <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Analysis for {lead.source_platform} ID: {String(lead.id).split('-')[0]}</p>
                </div>
              </div>
              <button 
                onClick={() => setShowModal(false)}
                className="p-2 text-gray-400 hover:text-gray-900 hover:bg-gray-50 rounded-full transition-colors"
              >
                <X size={24} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-8 no-scrollbar">
              {/* Intent Section */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Buyer Intent</h3>
                  <div className="flex items-center gap-2">
                    <ReadinessBadge level={lead.readiness_level} />
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-50 border border-blue-100 rounded-md text-blue-600">
                      <Zap size={12} className="fill-current" />
                      <span className="text-[10px] font-bold">{lead.deal_probability}% Conversion Prob.</span>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 border-l-4 border-blue-500 p-6 rounded-r-xl">
                  <p className="text-lg text-gray-900 font-medium leading-relaxed italic">
                    "{lead.buyer_request_snippet}"
                  </p>
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: 'Competition', value: `${lead.competition_count} Sellers`, icon: <Users size={16} /> },
                  { label: 'Reliability', value: `${lead.contact_reliability_score}%`, icon: <CheckCircle2 size={16} /> },
                  { label: 'Response Window', value: lead.optimal_response_window, icon: <Clock size={16} />, color: 'text-blue-600' },
                  { label: 'Market Demand', value: lead.seasonal_demand || 'Stable', icon: <BarChart3 size={16} /> }
                ].map((stat, i) => (
                  <div key={i} className="bg-white border border-gray-100 p-4 rounded-xl shadow-sm">
                    <div className="flex items-center gap-2 text-gray-400 mb-1">
                      {stat.icon}
                      <span className="text-[10px] font-bold uppercase tracking-wider">{stat.label}</span>
                    </div>
                    <p className={`text-sm font-bold ${stat.color || 'text-gray-900'}`}>{stat.value}</p>
                  </div>
                ))}
              </div>

              {/* Recommended Outreach */}
              <div className="space-y-4">
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Recommended Outreach</h3>
                <div className="bg-amber-50 border border-amber-100 rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <MessageSquare size={16} className="text-amber-600" />
                    <span className="text-sm font-bold text-amber-600">Key Talking Points</span>
                  </div>
                  <ul className="space-y-3">
                    {lead.talking_points?.map((point, i) => (
                      <li key={i} className="flex gap-3 text-sm text-gray-600 leading-relaxed">
                        <span className="text-amber-500 font-bold mt-1">•</span>
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-gray-100 bg-gray-50 flex flex-col sm:flex-row gap-3">
              <button 
                onClick={handleContact}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 transition-all active:scale-95 shadow-lg shadow-blue-600/10 text-base"
              >
                <ExternalLink size={20} />
                Contact on Platform
              </button>
              <button 
                onClick={() => setShowModal(false)}
                className="bg-white border border-gray-200 text-gray-500 hover:text-gray-900 font-bold py-4 px-8 rounded-xl transition-all"
              >
                Dismiss Report
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default LeadCard;
