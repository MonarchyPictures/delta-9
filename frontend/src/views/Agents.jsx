import React, { useState } from 'react';
import { User, Plus, Shield, Bell } from 'lucide-react';
import getApiUrl from '../config';

const Agents = ({ agents, loading, onCreateAgent }) => {
  return (
    <div className="flex-1 bg-black p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex justify-between items-center">
          <h1 className="text-4xl font-black text-white italic tracking-tighter uppercase">Market Agents</h1>
          <button 
            onClick={onCreateAgent}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-2xl font-bold transition-all shadow-lg shadow-blue-600/20"
          >
            <Plus size={20} /> Deploy New Agent
          </button>
        </div>

        {loading ? (
          <div className="text-center py-20 text-white/20 font-black uppercase tracking-[0.5em] animate-pulse">Consulting Neural Nodes...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents && agents.length > 0 ? agents.map((agent) => (
              <div key={agent.id} className="bg-white/5 border border-white/10 rounded-3xl p-6 space-y-4 hover:border-blue-600/50 transition-all group">
                <div className="flex justify-between items-start">
                  <div className="w-12 h-12 bg-blue-600/10 rounded-2xl flex items-center justify-center text-blue-500 group-hover:bg-blue-600 group-hover:text-white transition-all">
                    <Shield size={24} />
                  </div>
                  <div className="flex gap-2">
                     <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${agent.is_active ? 'bg-green-500/10 text-green-500' : 'bg-white/10 text-white/40'}`}>
                       {agent.is_active ? 'Active' : 'Standby'}
                     </span>
                  </div>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white tracking-tight">{agent.name}</h3>
                  <p className="text-white/40 text-xs italic">Hunting: {agent.query} in {agent.location}</p>
                </div>
                <div className="pt-4 border-t border-white/5 flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-white/40">
                  <div className="flex items-center gap-2"><Bell size={12}/> Alerts Enabled</div>
                  <div>Score: {agent.min_intent_score * 100}%</div>
                </div>
              </div>
            )) : (
              <div className="col-span-full py-20 bg-white/5 border border-white/10 rounded-3xl text-center">
                <p className="text-white/40 font-bold uppercase tracking-widest">No agents deployed. Start hunting today.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Agents;