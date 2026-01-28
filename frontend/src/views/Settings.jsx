import React from 'react';

const Settings = ({ notificationsEnabled, setNotificationsEnabled, soundEnabled, setSoundEnabled }) => {
  return (
    <div className="flex-1 bg-black p-8 text-white overflow-y-auto">
      <div className="max-w-2xl mx-auto space-y-12">
        <h1 className="text-4xl font-black italic tracking-tighter">SETTINGS</h1>
        
        <div className="space-y-6">
          <div className="bg-white/5 border border-white/10 rounded-3xl p-6 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-lg">Push Notifications</h3>
              <p className="text-white/40 text-sm italic">Alert me when new leads appear in Nairobi</p>
            </div>
            <button 
              onClick={() => setNotificationsEnabled(!notificationsEnabled)}
              className={`w-14 h-8 rounded-full transition-all ${notificationsEnabled ? 'bg-blue-600' : 'bg-white/10'}`}
            >
              <div className={`w-6 h-6 bg-white rounded-full transition-all transform ${notificationsEnabled ? 'translate-x-7' : 'translate-x-1'}`} />
            </button>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-3xl p-6 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-lg">Alert Sound</h3>
              <p className="text-white/40 text-sm italic">Play a sound for high-confidence intents</p>
            </div>
            <button 
              onClick={() => setSoundEnabled(!soundEnabled)}
              className={`w-14 h-8 rounded-full transition-all ${soundEnabled ? 'bg-blue-600' : 'bg-white/10'}`}
            >
              <div className={`w-6 h-6 bg-white rounded-full transition-all transform ${soundEnabled ? 'translate-x-7' : 'translate-x-1'}`} />
            </button>
          </div>
        </div>

        <div className="pt-12 border-t border-white/10">
          <p className="text-[10px] font-black uppercase tracking-[0.4em] text-white/20">Production Version 1.0.0 // Delta9</p>
        </div>
      </div>
    </div>
  );
};

export default Settings;