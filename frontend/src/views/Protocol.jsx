import React from 'react';
import { motion } from 'framer-motion';
import { 
  Shield, Zap, Database, Globe, Lock, 
  Activity, ChevronLeft, Terminal, Cpu,
  Search, Filter, CheckCircle2, AlertTriangle
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Protocol = () => {
  const navigate = useNavigate();

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { 
      opacity: 1,
      transition: { staggerChildren: 0.1, duration: 0.5 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <div className="flex-1 min-h-full bg-slate-950 text-slate-200">
      <div className="max-w-5xl mx-auto p-6 md:p-12 space-y-12">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-4">
            <button 
              onClick={() => navigate(-1)}
              className="group flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
            >
              <ChevronLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
              <span className="text-[10px] font-black uppercase tracking-widest">Return to Fleet</span>
            </button>
            <div className="space-y-2">
              <h1 className="text-4xl md:text-6xl font-black text-white tracking-tighter italic uppercase leading-none">
                System <span className="text-brand-primary">Protocols</span>
              </h1>
              <p className="text-slate-400 text-sm font-medium max-w-2xl">
                The technical operational standards governing the Delta-9 autonomous discovery engine and neural classification pipeline.
              </p>
            </div>
          </div>
          
          <div className="hidden md:block">
            <div className="px-4 py-2 bg-brand-primary/10 rounded-full border border-brand-primary/20 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-brand-primary animate-pulse" />
              <span className="text-[10px] font-black uppercase tracking-widest text-brand-primary">Classified: Level 4</span>
            </div>
          </div>
        </div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-1 gap-8"
        >
          {/* Phase 1: Autonomous Discovery */}
          <motion.section variants={itemVariants} className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8 space-y-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-brand-primary/20 rounded-2xl text-brand-primary">
                <Search size={24} />
              </div>
              <div>
                <h3 className="text-xl font-black text-white uppercase tracking-tighter">01. Autonomous Discovery</h3>
                <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">Phase One: Signal Capture</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
              <div className="space-y-4">
                <p className="text-slate-400 leading-relaxed">
                  The discovery engine utilizes multi-source scraping across major social platforms (Facebook, X, Reddit) and search engines (Google, DuckDuckGo). 
                </p>
                <ul className="space-y-2">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 size={14} className="text-brand-primary mt-1 shrink-0" />
                    <span>Real-time platform polling with rotating browser fingerprints.</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 size={14} className="text-brand-primary mt-1 shrink-0" />
                    <span>Geo-fenced search optimization targeting specific regions (Kenya, Nairobi, Mombasa).</span>
                  </li>
                </ul>
              </div>
              <div className="bg-slate-950/50 rounded-2xl p-4 border border-slate-800/50 font-mono text-[11px] text-brand-primary/80">
                <div className="flex items-center gap-2 mb-2 text-slate-500">
                  <Terminal size={12} />
                  <span>discovery_params.json</span>
                </div>
                {`{
  "search_depth": "aggressive",
  "locations": ["Nairobi", "Mombasa", "Kisumu"],
  "platforms": ["fb_groups", "x_realtime", "reddit_local"],
  "query_expansion": true
}`}
              </div>
            </div>
          </motion.section>

          {/* Phase 2: Neural Classification */}
          <motion.section variants={itemVariants} className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8 space-y-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-status-hot/20 rounded-2xl text-status-hot">
                <Filter size={24} />
              </div>
              <div>
                <h3 className="text-xl font-black text-white uppercase tracking-tighter">02. Neural Intent Classification</h3>
                <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">Phase Two: Intelligence Verification</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
              <div className="space-y-4">
                <p className="text-slate-400 leading-relaxed">
                  Delta-9 enforces <span className="text-white font-bold italic">Strict Buyer Intent</span> logic. Every signal must pass a multi-pass NLP verification to filter out sellers, advertisers, and service providers.
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-success/10 border border-success/20 rounded-xl">
                    <p className="text-[10px] font-black uppercase text-success mb-1">Pass Conditions</p>
                    <p className="text-[11px]">Explicit demand signals like "looking for", "need to buy", "where can I get".</p>
                  </div>
                  <div className="p-3 bg-status-hot/10 border border-status-hot/20 rounded-xl">
                    <p className="text-[10px] font-black uppercase text-status-hot mb-1">Fail Conditions</p>
                    <p className="text-[11px]">Selling language, price lists, "DM for order", or e-commerce links.</p>
                  </div>
                </div>
              </div>
              <div className="bg-slate-950/50 rounded-2xl p-4 border border-slate-800/50 font-mono text-[11px] text-status-hot/80">
                <div className="flex items-center gap-2 mb-2 text-slate-500">
                  <Cpu size={12} />
                  <span>intent_logic_v4.py</span>
                </div>
                {`def verify_intent(content):
    if any(seller_kw in content):
        return INTENT_SELLER # AUTO-EXCLUDE
    if any(buyer_kw in content):
        return INTENT_BUYER # PROCEED
    return INTENT_UNKNOWN # DISCARD`}
              </div>
            </div>
          </motion.section>

          {/* Phase 3: Fleet Deployment */}
          <motion.section variants={itemVariants} className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8 space-y-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-success/20 rounded-2xl text-success">
                <Activity size={24} />
              </div>
              <div>
                <h3 className="text-xl font-black text-white uppercase tracking-tighter">03. High-Priority Delivery</h3>
                <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">Phase Three: Actionable Intelligence</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm text-center">
              <div className="p-6 bg-slate-950/30 rounded-2xl border border-slate-800/50 space-y-3">
                <Zap size={24} className="mx-auto text-brand-primary" />
                <h4 className="font-black uppercase text-[11px] tracking-widest">Sub-Second Delivery</h4>
                <p className="text-slate-500 text-[11px]">Real-time polling ensures leads reach the dashboard within seconds of discovery.</p>
              </div>
              <div className="p-6 bg-slate-950/30 rounded-2xl border border-slate-800/50 space-y-3">
                <Shield size={24} className="mx-auto text-success" />
                <h4 className="font-black uppercase text-[11px] tracking-widest">Verified Contacts</h4>
                <p className="text-slate-500 text-[11px]">Automated extraction of phone numbers and social profiles from verified buyers.</p>
              </div>
              <div className="p-6 bg-slate-950/30 rounded-2xl border border-slate-800/50 space-y-3">
                <Database size={24} className="mx-auto text-status-warm" />
                <h4 className="font-black uppercase text-[11px] tracking-widest">SQLite Resiliency</h4>
                <p className="text-slate-500 text-[11px]">System maintains 100% operational capacity using SQLite fallback when Redis is unavailable.</p>
              </div>
            </div>
          </motion.section>

          {/* Safety & Compliance */}
          <motion.section variants={itemVariants} className="bg-brand-primary/5 border border-brand-primary/20 rounded-3xl p-8">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-brand-primary/20 rounded-2xl text-brand-primary mt-1">
                <Lock size={20} />
              </div>
              <div className="space-y-4">
                <h3 className="text-lg font-black text-white uppercase tracking-tighter italic">Operational Safety Protocol</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  To prevent platform detection, Delta-9 employs a non-linear discovery rhythm. Agents are programmed with randomized cooldown periods and human-like browsing patterns. 
                  <span className="block mt-2 text-brand-primary/80 font-bold">WARNING: Manual overriding of these safety protocols via 'Aggressive Discovery' mode may increase IP visibility.</span>
                </p>
              </div>
            </div>
          </motion.section>
        </motion.div>

        {/* Footer */}
        <div className="pt-12 border-t border-slate-800 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-4 grayscale opacity-50">
             <div className="h-6 w-24 bg-slate-800 rounded animate-pulse" />
             <div className="h-6 w-24 bg-slate-800 rounded animate-pulse" />
          </div>
          <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.3em]">
            Delta-9 Intelligence Systems © 2026 // No Unauthorized Access
          </p>
        </div>
      </div>
    </div>
  );
};

export default Protocol;
