import React, { useState, useRef, useEffect } from 'react';
import { Radar, Plus, User, Bell, Menu, X, Clock, Trash2, Settings } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const Header = ({ 
  onCreateAgent, 
  activeTab, 
  onTabChange, 
  notifications = [], 
  setNotifications,
  notificationsEnabled,
  setNotificationsEnabled,
  onNotificationClick
}) => {
  const [showNotifications, setShowNotifications] = useState(false);
  const dropdownRef = useRef(null);
  
  const navItems = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'leads', label: 'Leads' },
    { id: 'agents', label: 'Agents' },
    { id: 'settings', label: 'Settings' },
  ];

  const unreadCount = notifications.filter(n => n.unread).length;

  const formatTime = (dateStr) => {
    if (!dateStr) return 'Just now';
    try {
      const date = new Date(dateStr);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      return date.toLocaleDateString();
    } catch (e) {
      return 'Recently';
    }
  };

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkAsRead = (id) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, unread: false } : n));
  };

  const handleClearAll = () => {
    setNotifications([]);
    setShowNotifications(false);
  };

  const handleItemClick = async (notif) => {
    handleMarkAsRead(notif.id);
    setShowNotifications(false);
    
    // First try to find the lead to get its post_link
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/leads/${notif.lead_id}`);
      if (res.ok) {
        const lead = await res.json();
        if (lead && lead.post_link) {
          window.open(lead.post_link, '_blank');
        }
      }
    } catch (err) {
      console.error("Failed to fetch lead link from notification:", err);
    }
    
    // Also trigger the dashboard view to focus on this lead if needed
    onNotificationClick(notif.lead_id);
  };

  return (
    <header className="h-16 fixed top-0 left-0 right-0 bg-white/80 backdrop-blur-md border-b border-gray-100 z-[100] px-4 md:px-8">
      <div className="max-w-7xl mx-auto h-full flex items-center justify-between relative">
        {/* Logo Left */}
        <div 
          className="flex items-center gap-3 cursor-pointer group" 
          onClick={() => onTabChange('dashboard')}
          role="button"
          tabIndex={0}
          aria-label="Go to Dashboard"
          onKeyDown={(e) => e.key === 'Enter' && onTabChange('dashboard')}
        >
          <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-600/20 group-hover:scale-110 transition-transform duration-300">
            <Radar size={20} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight hidden sm:block">
            Delta<span className="text-blue-600">9</span>
          </h1>
        </div>

        {/* Navigation Center (Desktop) */}
        <nav className="hidden md:flex items-center gap-2" role="navigation">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`px-5 py-2 text-xs font-bold uppercase tracking-widest rounded-xl transition-all duration-200 ${
                activeTab === item.id
                  ? 'text-blue-600 bg-blue-50'
                  : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
              }`}
              aria-current={activeTab === item.id ? 'page' : undefined}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* User Menu Right */}
        <div className="flex items-center gap-3 md:gap-5">
          {/* Notification Bell */}
          <div className="relative" ref={dropdownRef}>
            <button 
              onClick={() => setShowNotifications(!showNotifications)}
              className={`p-2.5 rounded-xl transition-all relative group ${
                showNotifications 
                  ? 'text-blue-600 bg-blue-50' 
                  : 'text-gray-500 hover:text-blue-600 hover:bg-blue-50'
              }`}
              aria-label="View Notifications"
              aria-expanded={showNotifications}
            >
              <Bell size={20} />
              {unreadCount > 0 && notificationsEnabled && (
                <span className="absolute top-2.5 right-2.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 bg-red-500 rounded-full border-2 border-white text-[10px] font-bold text-white shadow-sm group-hover:scale-110 transition-transform">
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </button>

            {/* Notification Dropdown */}
            <AnimatePresence>
              {showNotifications && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className="absolute right-0 mt-3 w-[360px] max-w-[90vw] bg-white border border-gray-100 rounded-2xl shadow-2xl overflow-hidden z-[110]"
                >
                  {/* Header */}
                  <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between bg-white/50 backdrop-blur-sm sticky top-0 z-10">
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-sm text-gray-900">Notifications</h3>
                      {unreadCount > 0 && (
                        <span className="px-1.5 py-0.5 bg-blue-50 text-blue-600 text-[10px] font-bold rounded-md">
                          {unreadCount} New
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-3">
                      {/* Notifications Toggle */}
                      <div className="flex items-center gap-2 pr-3 border-r border-gray-100">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Alerts</span>
                        <button
                          onClick={() => setNotificationsEnabled(!notificationsEnabled)}
                          className={`w-8 h-4 rounded-full relative transition-colors duration-200 ${
                            notificationsEnabled ? 'bg-blue-600' : 'bg-gray-200'
                          }`}
                          role="switch"
                          aria-checked={notificationsEnabled}
                        >
                          <motion.div
                            animate={{ x: notificationsEnabled ? 16 : 2 }}
                            className="absolute top-1 w-2 h-2 bg-white rounded-full shadow-sm"
                          />
                        </button>
                      </div>

                      {notifications.length > 0 && (
                        <button 
                          onClick={handleClearAll}
                          className="text-gray-400 hover:text-red-500 transition-colors"
                          title="Clear all"
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* List */}
                  <div className="max-h-[400px] overflow-y-auto custom-scrollbar bg-white">
                    {notifications.length > 0 ? (
                      <div className="divide-y divide-gray-50">
                        <AnimatePresence initial={false}>
                          {notifications.map((notif) => (
                            <motion.div
                              key={notif.id}
                              initial={{ opacity: 0, y: 20 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, x: 20 }}
                              transition={{ duration: 0.3, ease: "easeOut" }}
                              className={`group p-4 hover:bg-gray-50 transition-all cursor-pointer relative overflow-hidden ${
                                notif.unread ? 'bg-blue-50/30' : ''
                              }`}
                              onClick={() => handleItemClick(notif)}
                            >
                              {notif.unread && (
                                <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-600" />
                              )}
                              
                              <div className="flex gap-4">
                                <div className={`mt-1 w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border transition-colors ${
                                  notif.unread 
                                    ? 'bg-blue-600 text-white border-blue-600 shadow-sm' 
                                    : 'bg-gray-50 text-gray-400 border-gray-100'
                                }`}>
                                  <Zap size={18} className={notif.unread ? 'animate-pulse' : ''} />
                                </div>
                                
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center justify-between gap-2 mb-1">
                                    <span className={`text-[10px] font-black uppercase tracking-widest ${
                                      notif.unread ? 'text-blue-600' : 'text-gray-400'
                                    }`}>
                                      {notif.message.includes('🚨') ? 'Urgent Alert' : 'Discovery Match'}
                                    </span>
                                    <span className="text-[10px] text-gray-400 whitespace-nowrap font-bold flex items-center gap-1">
                                      <Clock size={10} />
                                      {formatTime(notif.created_at)}
                                    </span>
                                  </div>
                                  
                                  <p className={`text-xs leading-relaxed transition-colors line-clamp-2 ${
                                    notif.unread ? 'text-gray-900 font-bold' : 'text-gray-500'
                                  }`}>
                                    {notif.message.replace('🚨 REAL-TIME ALERT: ', '').replace('URGENT: ', '')}
                                  </p>

                                  <div className="mt-2 flex items-center gap-2">
                                    <div className="px-2 py-0.5 bg-gray-100 rounded text-[9px] font-bold text-gray-500 uppercase tracking-tighter">
                                      Lead ID: {notif.lead_id.substring(0, 8)}
                                    </div>
                                    <div className="flex-1 h-px bg-gray-50" />
                                    <span className="text-[10px] font-bold text-blue-600 group-hover:translate-x-1 transition-transform flex items-center gap-1">
                                      View Lead <ExternalLink size={10} />
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </motion.div>
                          ))}
                        </AnimatePresence>
                      </div>
                    ) : (
                      <div className="px-8 py-12 text-center space-y-3">
                        <div className="w-12 h-12 bg-gray-50 rounded-2xl flex items-center justify-center mx-auto text-gray-300">
                          <Bell size={24} />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-gray-500">No notifications</p>
                          <p className="text-xs text-gray-400">You're all caught up!</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Footer */}
                  {notifications.length > 0 && (
                    <div className="p-3 border-t border-gray-100 bg-gray-50 text-center">
                      <button 
                        onClick={() => {
                          onTabChange('leads');
                          setShowNotifications(false);
                        }}
                        className="text-xs font-bold text-blue-600 hover:text-blue-700 transition-colors uppercase tracking-widest"
                      >
                        View All Leads
                      </button>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          
          <div className="h-6 w-[1px] bg-gray-100 hidden md:block"></div>

          <button 
            onClick={onCreateAgent}
            className="hidden md:flex items-center gap-2.5 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-widest transition-all shadow-lg shadow-blue-600/20 active:scale-95"
            aria-label="Create New Agent"
          >
            <Plus size={18} />
            <span>Create Agent</span>
          </button>

          <button 
            className="flex items-center gap-2 p-1.5 hover:bg-gray-100 rounded-2xl transition-all border border-transparent hover:border-gray-200 group"
            aria-label="User Profile"
            onClick={() => onTabChange('settings')}
          >
            <div className="w-8 h-8 bg-gray-50 rounded-xl flex items-center justify-center border border-gray-100 group-hover:border-blue-600/30 transition-colors">
              <User size={18} className="text-gray-500" />
            </div>
          </button>

          {/* Mobile Menu Toggle */}
          <button 
            className="md:hidden p-2 text-gray-500 hover:bg-gray-100 rounded-xl transition-colors"
            aria-label="Toggle Mobile Menu"
          >
            <Menu size={24} />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
