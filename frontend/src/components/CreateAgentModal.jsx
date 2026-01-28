import React, { useState } from 'react';
import { AgentFailedState } from './UXStates';
import { X, CheckCircle2, Zap, Shield, Cpu, Target, Bell, Globe, Search, Power } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const CreateAgentModal = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    name: '',
    query: '',
    location: 'Kenya',
    radius: 50,
    min_intent_score: 0.7,
    is_active: 1,
    enable_alerts: 1,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [errors, setErrors] = useState({});

  const validateForm = () => {
    const newErrors = {};
    if (!formData.name.trim()) newErrors.name = 'Agent identity is required';
    if (formData.name.length < 3) newErrors.name = 'Identity must be at least 3 characters';
    if (!formData.query.trim()) newErrors.query = 'Discovery keywords are required';
    if (formData.query.length < 3) newErrors.query = 'Keywords must be at least 3 characters';
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;
    
    setIsSubmitting(true);
    setHasError(false);
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${apiUrl}/agents`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) throw new Error('Failed to deploy agent');

      setIsSubmitting(false);
      setIsSuccess(true);
      if (onSuccess) onSuccess();
      setTimeout(() => {
        setIsSuccess(false);
        onClose();
        setFormData({ 
          name: '', 
          query: '', 
          location: 'Kenya', 
          radius: 50, 
          min_intent_score: 0.7, 
          is_active: 1, 
          enable_alerts: 1 
        });
      }, 2500);
    } catch (err) {
      setIsSubmitting(false);
      setHasError(true);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white border border-gray-200 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in slide-in-from-bottom-4 duration-300">
        {isSuccess ? (
          <div className="p-12 text-center flex flex-col items-center justify-center min-h-[400px]">
            <div className="w-20 h-20 bg-success/10 rounded-full flex items-center justify-center mb-6 border border-success/20 shadow-lg shadow-success/10">
              <CheckCircle2 size={40} className="text-success" />
            </div>
            <h3 className="text-2xl font-bold text-black mb-2">Agent Successfully Deployed</h3>
            <p className="text-black text-sm leading-relaxed max-w-xs mx-auto font-bold">
              Your autonomous agent <span className="text-blue-600 font-black">{formData.name}</span> is now patrolling the <span className="font-black text-black">{formData.location}</span> market.
            </p>
          </div>
        ) : hasError ? (
          <div className="p-8">
            <AgentFailedState onRetry={() => setHasError(false)} />
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col">
            {/* Modal Header */}
            <div className="px-8 py-6 border-b border-gray-200 flex justify-between items-center bg-white">
              <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-blue-600/10 rounded-xl">
                    <Cpu size={24} className="text-blue-600" />
                  </div>
                  <div>
                    <h2 className="text-xl font-black text-black leading-tight uppercase italic tracking-tighter">Configure AI Agent</h2>
                    <p className="text-[10px] text-black font-black uppercase tracking-widest">Define parameters for autonomous discovery</p>
                  </div>
                </div>
              <button 
                type="button" 
                onClick={onClose} 
                className="p-2 text-black hover:text-black hover:bg-gray-100 rounded-lg transition-all"
              >
                <X size={20} />
              </button>
            </div>


            {/* Modal Content */}
            <div className="p-8 space-y-6 max-h-[70vh] overflow-y-auto no-scrollbar">
              {/* Agent Identity */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Target size={14} className="text-blue-600" />
                  <label className="text-[10px] font-black text-black uppercase tracking-widest">Agent Identity</label>
                </div>
                <input
                    required
                    type="text"
                    placeholder="e.g. Luxury Car Hunter"
                    className={`w-full bg-gray-50 border rounded-xl px-4 py-3.5 text-black text-sm font-bold focus:ring-4 outline-none transition-all placeholder:text-black italic ${
                      errors.name ? 'border-red-500 focus:ring-red-500/10' : 'border-gray-200 focus:border-blue-600 focus:ring-blue-600/10'
                    }`}
                    value={formData.name}
                    onChange={(e) => {
                      setFormData({ ...formData, name: e.target.value });
                      if (errors.name) setErrors({ ...errors, name: null });
                    }}
                  />
                {errors.name && <p className="text-[10px] font-black text-red-500 uppercase tracking-widest">{errors.name}</p>}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Geography */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Globe size={14} className="text-blue-600" />
                    <label className="text-[10px] font-black text-black uppercase tracking-widest">Target Geography</label>
                  </div>
                  <div className="relative">
                    <select
                      required
                      className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 text-black text-sm font-bold focus:border-blue-600 focus:ring-4 focus:ring-blue-600/10 outline-none transition-all cursor-pointer appearance-none italic"
                      value={formData.location}
                      onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    >
                      <option value="Kenya">Kenya (All)</option>
                      <option value="Nairobi">Nairobi</option>
                      <option value="Mombasa">Mombasa</option>
                      <option value="Kisumu">Kisumu</option>
                      <option value="Nakuru">Nakuru</option>
                    </select>
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-black">
                      <Globe size={14} />
                    </div>
                  </div>
                </div>

                {/* Search Query */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Search size={14} className="text-blue-600" />
                    <label className="text-[10px] font-black text-black uppercase tracking-widest">Discovery Keywords</label>
                  </div>
                  <input
                    required
                    type="text"
                    placeholder="e.g. Toyota Prado"
                    className={`w-full bg-gray-50 border rounded-xl px-4 py-3.5 text-black text-sm font-bold focus:ring-4 outline-none transition-all placeholder:text-black italic ${
                      errors.query ? 'border-red-500 focus:ring-red-500/10' : 'border-gray-200 focus:border-blue-600 focus:ring-blue-600/10'
                    }`}
                    value={formData.query}
                    onChange={(e) => {
                      setFormData({ ...formData, query: e.target.value });
                      if (errors.query) setErrors({ ...errors, query: null });
                    }}
                  />
                  {errors.query && <p className="text-[10px] font-black text-red-500 uppercase tracking-widest">{errors.query}</p>}
                </div>

                {/* Radius and Intent Score */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Target size={14} className="text-blue-600" />
                      <label className="text-[10px] font-black text-black uppercase tracking-widest">Radius (km)</label>
                    </div>
                    <input
                      type="number"
                      min="1"
                      max="1000"
                      className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 text-black text-sm font-bold focus:border-blue-600 focus:ring-4 focus:ring-blue-600/10 outline-none transition-all"
                      value={formData.radius}
                      onChange={(e) => setFormData({ ...formData, radius: parseInt(e.target.value) || 50 })}
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Shield size={14} className="text-blue-600" />
                      <label className="text-[10px] font-black text-black uppercase tracking-widest">Min Confidence</label>
                    </div>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="1"
                      className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3.5 text-black text-sm font-bold focus:border-blue-600 focus:ring-4 focus:ring-blue-600/10 outline-none transition-all"
                      value={formData.min_intent_score}
                      onChange={(e) => setFormData({ ...formData, min_intent_score: parseFloat(e.target.value) || 0.7 })}
                    />
                  </div>
                </div>
              </div>

              {/* Toggles */}
              <div className="space-y-4 pt-2">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-100">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-white border border-gray-200 flex items-center justify-center">
                      <Power size={18} className={formData.is_active ? 'text-blue-600' : 'text-gray-400'} />
                    </div>
                    <div>
                      <span className="text-xs font-black text-black block uppercase tracking-wider italic">Aggressive Discovery</span>
                      <span className="text-[10px] text-black font-black uppercase tracking-widest">Enhanced scanning frequency</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, is_active: formData.is_active === 1 ? 0 : 1 })}
                    className={`w-12 h-6 rounded-full relative transition-colors duration-300 ${formData.is_active === 1 ? 'bg-blue-600' : 'bg-gray-200'}`}
                    role="switch"
                    aria-checked={formData.is_active === 1}
                    aria-label="Aggressive Discovery Toggle"
                  >
                    <motion.div 
                      animate={{ x: formData.is_active === 1 ? 26 : 2 }}
                      transition={{ type: "spring", stiffness: 500, damping: 30 }}
                      className="absolute top-1 w-4 h-4 rounded-full bg-white shadow-sm" 
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-100">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-white border border-gray-200 flex items-center justify-center">
                      <Bell size={18} className={formData.enable_alerts ? 'text-orange-500' : 'text-gray-400'} />
                    </div>
                    <div>
                      <span className="text-xs font-black text-black block uppercase tracking-wider italic">Real-time Notifications</span>
                      <span className="text-[10px] text-black font-black uppercase tracking-widest">Instant alerts on lead discovery</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setFormData({ ...formData, enable_alerts: formData.enable_alerts ? 0 : 1 })}
                    className={`w-12 h-6 rounded-full relative transition-colors duration-300 ${formData.enable_alerts === 1 ? 'bg-blue-600' : 'bg-gray-200'}`}
                    role="switch"
                    aria-checked={formData.enable_alerts === 1}
                    aria-label="Real-time Notifications Toggle"
                  >
                    <motion.div 
                      animate={{ x: formData.enable_alerts === 1 ? 26 : 2 }}
                      transition={{ type: "spring", stiffness: 500, damping: 30 }}
                      className="absolute top-1 w-4 h-4 rounded-full bg-white shadow-sm" 
                    />
                  </button>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-8 py-6 border-t border-gray-200 bg-white flex gap-3">
              <button 
                type="button"
                onClick={onClose}
                className="flex-1 px-6 py-3.5 text-black font-black uppercase tracking-widest hover:bg-gray-50 rounded-xl transition-all border border-gray-200 text-[10px]"
              >
                Cancel
              </button>
              <button 
                disabled={isSubmitting}
                type="submit"
                className="flex-[2] bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-black uppercase tracking-widest py-3.5 rounded-xl transition-all active:scale-[0.98] shadow-lg shadow-blue-600/20 flex items-center justify-center gap-2 text-[10px] italic"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Deploying...</span>
                  </>
                ) : (
                  <>
                    <Zap size={14} />
                    <span>Initialize Deployment</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default CreateAgentModal;
