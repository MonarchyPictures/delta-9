import React, { useState } from 'react';
import { 
  Settings as SettingsIcon, Shield, Bell, Zap, Database, Globe, Lock, 
  Sliders, Smartphone, Mail, Info, Cpu, Activity, 
  RefreshCcw, Save, AlertTriangle, CheckCircle2, ChevronRight,
  LayoutGrid
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const Settings = ({ notificationsEnabled, setNotificationsEnabled }) => {
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null); // 'success', 'error'
  const [health, setHealth] = useState(null);
  const [uiPreferences, setUiPreferences] = useState({
    compactMode: false,
    autoRefresh: true,
    showStats: true,
    animations: true
  });

  const toggleUiPreference = (key) => {
    setUiPreferences(prev => ({ ...prev, [key]: !prev[key] }));
  };

  React.useEffect(() => {
    const controller = new AbortController();
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const fetchHealth = async (signal) => {
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      try {
        const res = await fetch(`${apiUrl}/health`, {
          signal: signal
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        }
      } catch (err) {
        clearTimeout(timeoutId);
        if (err.name !== 'AbortError') {
          console.error("Health fetch failed:", err);
        }
      }
    };

    const fetchSettings = async (signal) => {
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      try {
        const res = await fetch(`${apiUrl}/settings`, {
          signal: signal
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          const data = await res.json();
          if (data) {
            setUiPreferences(prev => ({
              ...prev,
              compactMode: data.compactMode ?? prev.compactMode,
              autoRefresh: data.autoRefresh ?? prev.autoRefresh,
              showStats: data.showStats ?? prev.showStats,
              animations: data.animations ?? prev.animations
            }));
            if (data.notifications_enabled !== undefined) {
              setNotificationsEnabled(data.notifications_enabled);
            }
          }
        }
      } catch (err) {
        clearTimeout(timeoutId);
        if (err.name !== 'AbortError') {
          console.error("Settings fetch failed:", err);
        }
      }
    };

    fetchHealth(controller.signal);
    fetchSettings(controller.signal);
    const interval = setInterval(() => {
      const intervalController = new AbortController();
      fetchHealth(intervalController.signal);
    }, 10000);
    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, [setNotificationsEnabled]);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus(null);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    try {
      // Save all settings including UI preferences
      const settingsToSave = {
        ...uiPreferences,
        notifications_enabled: notificationsEnabled
      };
      
      const res = await fetch(`${apiUrl}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsToSave),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        setSaveStatus('success');
        setTimeout(() => setSaveStatus(null), 3000);
      } else {
        setSaveStatus('error');
      }
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name !== 'AbortError') {
        console.error("Save settings error:", err);
        setSaveStatus('error');
      }
    } finally {
      setIsSaving(false);
    }
  };

  const containerVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { staggerChildren: 0.1, duration: 0.4 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, x: -10 },
    visible: { opacity: 1, x: 0 }
  };

  return (
    <div className="flex-1 min-h-full bg-surface-tertiary/30">
      <div className="max-w-[1400px] mx-auto p-6 md:p-10 space-y-10">
        {/* Header Section */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-brand-primary/10 rounded-full border border-brand-primary/20">
              <SettingsIcon size={14} className="text-brand-primary" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-primary">System Control</span>
            </div>
            <div className="space-y-2">
              <h1 className="text-4xl md:text-5xl font-black text-text-primary tracking-tighter italic uppercase leading-none">
                Configuration
              </h1>
              <p className="text-text-tertiary text-sm font-medium max-w-xl">
                Fine-tune your autonomous discovery engine and system-wide intelligence parameters.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <AnimatePresence mode="wait">
              {saveStatus === 'success' && (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  className="flex items-center gap-2 px-4 py-2 bg-success/10 text-success border border-success/20 rounded-xl"
                >
                  <CheckCircle2 size={16} />
                  <span className="text-xs font-black uppercase tracking-widest">Config Synchronized</span>
                </motion.div>
              )}
            </AnimatePresence>
            <button 
              onClick={handleSave}
              disabled={isSaving}
              className="bg-text-primary hover:bg-slate-800 text-white px-8 py-4 rounded-2xl font-black uppercase tracking-widest text-xs shadow-xl shadow-text-primary/10 transition-all active:scale-95 flex items-center gap-3 disabled:opacity-50"
            >
              {isSaving ? (
                <RefreshCcw size={18} className="animate-spin" />
              ) : (
                <Save size={18} />
              )}
              {isSaving ? 'Encrypting...' : 'Push Configuration'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          {/* Main Settings Area */}
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="lg:col-span-2 space-y-10"
          >
            {/* Discovery Engine Section */}
            <section className="space-y-6">
              <div className="flex items-center gap-3 border-b border-surface-secondary pb-4">
                <div className="p-2 bg-brand-primary/10 rounded-lg text-brand-primary">
                  <Cpu size={20} />
                </div>
                <h3 className="text-sm font-black text-text-primary uppercase tracking-[0.2em]">Neural Engine</h3>
              </div>
              <div className="grid grid-cols-1 gap-4">
                <SettingCard 
                  variants={itemVariants}
                  icon={<Zap className="text-status-hot" size={20} />}
                  title="Aggressive Discovery"
                  description="Optimize agents for maximum frequency. May increase detection probability on strict platforms."
                  defaultActive={true}
                  badge="High Performance"
                />
                <SettingCard 
                  variants={itemVariants}
                  icon={<Database className="text-brand-primary" size={20} />}
                  title="Deep Signal Analysis"
                  description="Enable multi-pass AI processing for complex intent decryption and verification."
                  defaultActive={true}
                />
                <SettingCard 
                  variants={itemVariants}
                  icon={<Globe className="text-status-warm" size={20} />}
                  title="Global Node Expansion"
                  description="Automatically deploy discovery nodes beyond primary target geographies when signals are low."
                  defaultActive={false}
                />
              </div>
            </section>

            {/* Notifications Section */}
            <section className="space-y-6">
              <div className="flex items-center gap-3 border-b border-surface-secondary pb-4">
                <div className="p-2 bg-status-hot/10 rounded-lg text-status-hot">
                  <Bell size={20} />
                </div>
                <h3 className="text-sm font-black text-text-primary uppercase tracking-[0.2em]">Intelligence Alerts</h3>
              </div>
              <div className="grid grid-cols-1 gap-4">
                <SettingCard 
                  variants={itemVariants}
                  icon={<Smartphone className="text-brand-primary" size={20} />}
                  title="Real-time Radar Pings"
                  description="Receive immediate high-priority notifications for leads exceeding 90% intent confidence."
                  active={notificationsEnabled}
                  onToggle={setNotificationsEnabled}
                  badge="Critical"
                />
                <SettingCard 
                  variants={itemVariants}
                  icon={<Mail className="text-text-tertiary" size={20} />}
                  title="Daily Intelligence Digest"
                  description="A comprehensive report of all captured signals and market movement delivered to your inbox."
                  defaultActive={false}
                />
              </div>
            </section>

            {/* Security Section */}
            <section className="space-y-6">
              <div className="flex items-center gap-3 border-b border-surface-secondary pb-4">
                <div className="p-2 bg-success/10 rounded-lg text-success">
                  <Shield size={20} />
                </div>
                <h3 className="text-sm font-black text-text-primary uppercase tracking-[0.2em]">Fleet Security</h3>
              </div>
              <div className="grid grid-cols-1 gap-4">
                <SettingCard 
                  variants={itemVariants}
                  icon={<Lock className="text-success" size={20} />}
                  title="Identity Masking"
                  description="Rotate agent signatures and browser fingerprints to prevent platform flagging."
                  defaultActive={true}
                />
              </div>
            </section>

            {/* Interface Section */}
            <section className="space-y-6">
              <div className="flex items-center gap-3 border-b border-surface-secondary pb-4">
                <div className="p-2 bg-brand-primary/10 rounded-lg text-brand-primary">
                  <LayoutGrid size={20} />
                </div>
                <h3 className="text-sm font-black text-text-primary uppercase tracking-[0.2em]">Interface Preferences</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <SettingCard 
                  variants={itemVariants}
                  icon={<Activity className="text-brand-primary" size={18} />}
                  title="Smooth Animations"
                  description="Enable fluid micro-interactions across the dashboard."
                  active={uiPreferences.animations}
                  onToggle={() => toggleUiPreference('animations')}
                />
                <SettingCard 
                  variants={itemVariants}
                  icon={<RefreshCcw className="text-brand-primary" size={18} />}
                  title="Auto-Refresh"
                  description="Automatically synchronize fleet status every 30 seconds."
                  active={uiPreferences.autoRefresh}
                  onToggle={() => toggleUiPreference('autoRefresh')}
                />
              </div>
            </section>
          </motion.div>

          {/* Sidebar Info Area */}
          <div className="space-y-8">
            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-surface-primary border border-surface-secondary rounded-[2rem] p-8 space-y-8 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-black text-text-primary uppercase tracking-widest flex items-center gap-2">
                  <Activity size={16} className="text-brand-primary" />
                  Fleet Status
                </h4>
                <div className="px-2 py-1 bg-success/10 rounded-lg border border-success/20">
                  <span className="text-[9px] font-black text-success uppercase tracking-widest">Operational</span>
                </div>
              </div>

              <div className="space-y-6">
                <StatusItem 
                  label="System Status" 
                  value={health?.status === 'healthy' ? 'Operational' : 'Degraded'} 
                  status={health?.status === 'healthy' ? 'success' : 'warning'} 
                />
                <StatusItem 
                  label="API Connectivity" 
                  value={health?.services?.database === 'up' ? 'Database Online' : 'Database Offline'} 
                  status={health?.services?.database === 'up' ? 'success' : 'warning'} 
                />
                <StatusItem 
                  label="Task Queue" 
                  value={health?.services?.celery === 'up' ? 'Redis Connected' : 'Redis Offline'} 
                  status={health?.services?.celery === 'up' ? 'success' : 'warning'} 
                />
                <StatusItem 
                  label="Memory Usage" 
                  value={health?.metrics?.memory_usage || 'Calculating...'} 
                  status={parseInt(health?.metrics?.memory_usage) > 80 ? 'warning' : 'success'} 
                />
                <StatusItem 
                  label="CPU Load" 
                  value={health?.metrics?.cpu_usage || 'Calculating...'} 
                  status={parseInt(health?.metrics?.cpu_usage) > 80 ? 'warning' : 'success'} 
                />
              </div>

              <div className="pt-6 border-t border-surface-secondary">
                <button className="w-full bg-surface-tertiary hover:bg-surface-secondary text-text-primary font-black py-4 rounded-xl text-[10px] border border-surface-secondary transition-all uppercase tracking-widest flex items-center justify-center gap-2 group">
                  <RefreshCcw size={14} className="group-hover:rotate-180 transition-transform duration-500" />
                  Execute Full Diagnostics
                </button>
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-slate-950 rounded-[2rem] p-8 relative overflow-hidden group border border-slate-800 shadow-2xl"
            >
              <div className="absolute inset-0 opacity-10 pointer-events-none" 
                   style={{ backgroundImage: 'radial-gradient(#3B82F6 0.5px, transparent 0.5px)', backgroundSize: '20px 20px' }} />
              
              <div className="relative z-10 space-y-4">
                <div className="flex items-center gap-2 text-brand-primary">
                  <AlertTriangle size={16} />
                  <span className="text-[10px] font-black uppercase tracking-widest">Operational Warning</span>
                </div>
                <p className="text-xs text-slate-400 font-medium leading-relaxed">
                  Enabling <span className="text-white font-black italic">Aggressive Discovery</span> bypasses standard safety cooldowns. While discovery rate increases by 300%, it elevates the risk of temporary IP isolation.
                </p>
                <div className="pt-2">
                  <button className="text-brand-primary text-[10px] font-black uppercase tracking-widest flex items-center gap-1 hover:gap-2 transition-all">
                    View Protocol Documentation <ChevronRight size={12} />
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};

const SettingCard = ({ icon, title, description, defaultActive, badge, variants, active: controlledActive, onToggle }) => {
  const [internalActive, setInternalActive] = useState(defaultActive);
  const isControlled = controlledActive !== undefined;
  const active = isControlled ? controlledActive : internalActive;

  const handleToggle = () => {
    if (isControlled) {
      onToggle?.(!active);
    } else {
      setInternalActive(!active);
    }
  };

  return (
    <motion.div 
      variants={variants}
      className="bg-surface-primary border border-surface-secondary p-6 rounded-[1.5rem] flex items-center justify-between group hover:border-brand-primary/30 hover:shadow-xl transition-all duration-300 relative overflow-hidden"
    >
      <div className="flex items-center gap-6 flex-1 pr-8">
        <div className="w-14 h-14 bg-surface-tertiary rounded-2xl flex items-center justify-center border border-surface-secondary group-hover:bg-brand-primary/5 transition-all duration-500 group-hover:scale-110 group-hover:shadow-inner">
          {icon}
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h4 className="text-base font-black text-text-primary tracking-tight italic uppercase group-hover:text-brand-primary transition-colors">{title}</h4>
            {badge && (
              <span className="px-2 py-0.5 bg-brand-primary/10 text-brand-primary text-[8px] font-black uppercase tracking-[0.2em] rounded-md border border-brand-primary/20">
                {badge}
              </span>
            )}
          </div>
          <p className="text-xs text-text-tertiary font-medium leading-relaxed max-w-lg">{description}</p>
        </div>
      </div>

      <button 
        onClick={handleToggle}
        className={`w-14 h-7 rounded-full relative transition-all duration-500 active:scale-90 flex items-center px-1 group/toggle ${
          active ? 'bg-brand-primary shadow-lg shadow-brand-primary/30' : 'bg-surface-tertiary border border-surface-secondary hover:border-text-tertiary/30'
        }`}
        role="switch"
        aria-checked={active}
        aria-label={`Toggle ${title}`}
      >
        <div className={`w-5 h-5 bg-white rounded-full shadow-md transition-all duration-500 transform ${
          active ? 'translate-x-7 scale-110' : 'translate-x-0 scale-100'
        }`} />
      </button>
    </motion.div>
  );
};

const StatusItem = ({ label, value, status }) => {
  const statusColors = {
    success: 'bg-success',
    warning: 'bg-status-hot',
    default: 'bg-brand-primary'
  };

  return (
    <div className="flex items-center justify-between group">
      <div className="space-y-1">
        <p className="text-[10px] text-text-tertiary font-black uppercase tracking-widest">{label}</p>
        <p className="text-sm font-black text-text-primary group-hover:text-brand-primary transition-colors">{value}</p>
      </div>
      <div className={`w-1.5 h-1.5 rounded-full ${statusColors[status] || statusColors.default} animate-pulse`} />
    </div>
  );
};

export default Settings;
