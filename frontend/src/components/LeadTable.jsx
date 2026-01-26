import React, { useState, useEffect } from 'react';
import StatusBadge from './StatusBadge';
import { ArrowRight, ExternalLink, Zap, X, Shield, MapPin, Users, Target, Calendar, MessageSquare, Phone, Globe, ShieldCheck } from 'lucide-react';

const LeadTable = ({ leads, autoOpenId = null, onModalClose = () => {} }) => {
  const [selectedLead, setSelectedLead] = useState(null);

  useEffect(() => {
    if (autoOpenId && Array.isArray(leads)) {
      const lead = leads.find(l => String(l.id) === String(autoOpenId));
      if (lead) {
        setSelectedLead(lead);
      }
    }
  }, [autoOpenId, leads]);

  const handleEngage = async (e, lead) => {
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

  const whatsappUrl = selectedLead?.contact_phone ? `https://wa.me/${selectedLead.contact_phone.replace(/\D/g, '')}` : null;

  return (
    <div className="hidden md:block overflow-hidden bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-6 py-4">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Buyer</span>
              </th>
              <th className="px-6 py-4">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Platform</span>
              </th>
              <th className="px-6 py-4">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Confidence</span>
              </th>
              <th className="px-6 py-4">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Request</span>
              </th>
              <th className="px-6 py-4">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</span>
              </th>
              <th className="px-6 py-4 text-right">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Action</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {leads.map((lead) => (
              <tr 
                key={lead.id} 
                className="hover:bg-blue-50/30 transition-colors group cursor-pointer"
                onClick={() => setSelectedLead(lead)}
              >
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 font-bold text-xs">
                      {(lead.buyer_name || 'A')[0].toUpperCase()}
                    </div>
                    <div className="flex flex-col">
                      <span className="text-sm font-bold text-gray-900">{lead.buyer_name || 'Anonymous'}</span>
                      <span className="text-[11px] text-gray-500">{lead.location_raw}</span>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className="text-xs font-medium text-gray-600 px-2 py-1 bg-gray-100 rounded">
                    {lead.source_platform}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-col gap-1.5 w-24">
                    <div className="flex items-center justify-between text-[10px] font-bold">
                      <span className={lead.confidence_score >= 8 ? 'text-green-600' : 'text-amber-600'}>
                        {lead.confidence_score * 10}%
                      </span>
                    </div>
                    <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-500 ${
                          lead.confidence_score >= 8 ? 'bg-green-500' : 
                          lead.confidence_score >= 5 ? 'bg-amber-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${lead.confidence_score * 10}%` }}
                      />
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 max-w-xs">
                  <p className="text-sm text-gray-600 truncate italic">
                    "{lead.buyer_request_snippet}"
                  </p>
                </td>
                <td className="px-6 py-4">
                  <StatusBadge status={lead.status} />
                </td>
                <td className="px-6 py-4 text-right">
                  <button className="text-blue-600 hover:text-blue-800 font-bold text-sm">
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Analysis Modal */}
      {selectedLead && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-gray-900/60 backdrop-blur-sm" onClick={() => { setSelectedLead(null); onModalClose(); }} />
          
          <div className="bg-white w-full max-w-2xl max-h-[90vh] rounded-2xl shadow-2xl overflow-hidden flex flex-col relative z-10 animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-gray-100 flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600">
                  <ShieldCheck size={24} />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Lead Details</h2>
                  <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Source: {selectedLead.source_platform}</p>
                </div>
              </div>
              <button 
                onClick={() => {
                  setSelectedLead(null);
                  onModalClose();
                }}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-all"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="bg-gray-50 p-6 rounded-xl border border-gray-100">
                <p className="text-lg text-gray-900 font-medium italic leading-relaxed">
                  "{selectedLead.buyer_request_snippet}"
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-white border border-gray-100 p-4 rounded-xl shadow-sm">
                  <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider mb-1">Readiness</p>
                  <p className="text-sm font-bold text-red-600">{selectedLead.readiness_level}</p>
                </div>
                <div className="bg-white border border-gray-100 p-4 rounded-xl shadow-sm">
                  <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider mb-1">Probability</p>
                  <p className="text-sm font-bold text-amber-600">{selectedLead.deal_probability}%</p>
                </div>
                <div className="bg-white border border-gray-100 p-4 rounded-xl shadow-sm">
                  <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider mb-1">Confidence</p>
                  <p className="text-sm font-bold text-blue-600">{(selectedLead.intent_score * 100).toFixed(0)}%</p>
                </div>
                <div className="bg-white border border-gray-100 p-4 rounded-xl shadow-sm">
                  <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider mb-1">Market Trend</p>
                  <p className="text-sm font-bold text-green-600">{selectedLead.seasonal_demand || 'Stable'}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Buyer Details</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Name</span>
                      <span className="font-bold">{selectedLead.buyer_name || 'Anonymous'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Location</span>
                      <span className="font-bold">{selectedLead.location_raw}</span>
                    </div>
                  </div>
                </div>
                <div className="space-y-3">
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Signal Source</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Status</span>
                      <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${selectedLead.is_contact_verified ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                        {selectedLead.is_contact_verified ? 'Verified' : 'Unverified'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Discovered</span>
                      <span className="font-bold">{selectedLead.time_ago}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-6 border-t border-gray-100 bg-gray-50 flex flex-col sm:flex-row gap-3">
              <button 
                onClick={(e) => handleEngage(e, selectedLead)}
                className="flex-[2] bg-blue-600 hover:bg-blue-700 text-white font-bold py-3.5 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20 transition-all active:scale-95 text-sm"
              >
                <ExternalLink size={18} />
                <span>Contact Lead</span>
              </button>
              
              {whatsappUrl && (
                <button 
                  onClick={() => window.open(whatsappUrl, '_blank')}
                  className="flex-1 bg-green-500 hover:bg-green-600 text-white font-bold py-3.5 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-green-500/20 transition-all active:scale-95 text-sm"
                >
                  <Phone size={18} />
                  <span>WhatsApp</span>
                </button>
              )}
              
              <button 
                onClick={() => {
                  setSelectedLead(null);
                  onModalClose();
                }}
                className="flex-1 px-6 py-3.5 text-gray-500 font-bold hover:bg-gray-200 rounded-xl transition-all border border-gray-200 text-sm"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LeadTable;
