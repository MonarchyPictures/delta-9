import getApiUrl, { getApiKey } from '../config';
import React, { useState, useRef, useEffect } from 'react';
import { LayoutDashboard, Plus, User, Bell, Menu, X, Clock, Trash2, Settings, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const Header = ({ 
  notifications = [], 
  markAsRead,
  markAllAsRead,
  clearNotifications,
  notificationsEnabled,
  setNotificationsEnabled
}) => {
  const [showNotifications, setShowNotifications] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();
  
  const unreadCount = notifications.filter(n => n.is_read === 0).length;

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

  const handleClearAll = () => {
    clearNotifications();
    setShowNotifications(false);
  };

  const handleItemClick = async (notif) => {
    if (notif.is_read === 0) {
      markAsRead(notif.id);
    }
    setShowNotifications(false);
    
    // First try to find the lead to get its post_link
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      const res = await fetch(`${apiUrl}/leads/${notif.lead_id}`, {
        headers: {
          'X-API-Key': apiKey
        }
      });
      if (res.ok) {
        const lead = await res.json();
        if (lead && lead.post_link) {
          window.open(lead.post_link, '_blank');
        }
      }
    } catch (err) {
      console.error("Failed to fetch lead link from notification:", err);
    }
  };

  return (
    <header className="h-16 bg-black/50 backdrop-blur-md border-b border-white/10 z-[100] px-4 md:px-8">
      <div className="max-w-7xl mx-auto h-full flex items-center justify-end relative">
        {/* User Menu Right */}
        <div className="flex items-center gap-3 md:gap-5">
          {/* Notification Bell */}
          <div className="relative" ref={dropdownRef}>
            <button 
              onClick={() => setShowNotifications(!showNotifications)}
              className={`p-2.5 rounded-xl transition-all relative group ${
                showNotifications 
                  ? 'text-blue-600 bg-blue-600/10' 
                  : 'text-white/40 hover:text-blue-600 hover:bg-blue-600/10'
              }`}
              aria-label="View Notifications"
              aria-expanded={showNotifications}
            >
              <Bell size={20} />
              {unreadCount > 0 && notificationsEnabled && (
                <span className="absolute top-2.5 right-2.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 bg-red-500 rounded-full border-2 border-black text-[10px] font-bold text-white shadow-sm group-hover:scale-110 transition-transform">
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
                  className="absolute right-0 mt-3 w-[360px] max-w-[90vw] bg-[#0A0A0A] border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-[110]"
                >
                  {/* Header */}
                  <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between bg-black/50 backdrop-blur-sm sticky top-0 z-10">
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-sm text-white">Notifications</h3>
                      {unreadCount > 0 && (
                        <span className="px-1.5 py-0.5 bg-blue-600/10 text-blue-600 text-[10px] font-bold rounded-md">
                          {unreadCount} New
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-3">
                      {/* Notifications Toggle */}
                      <div className="flex items-center gap-2 pr-3 border-r border-white/5">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-white/20">Alerts</span>
                        <button
                          onClick={() => setNotificationsEnabled(!notificationsEnabled)}
                          className={`w-8 h-4 rounded-full relative transition-colors duration-200 ${
                            notificationsEnabled ? 'bg-blue-600' : 'bg-white/10'
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
                          className="text-white/20 hover:text-red-500 transition-colors"
                          title="Clear all"
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* List */}
                  <div className="max-h-[400px] overflow-y-auto custom-scrollbar bg-[#0A0A0A]">
                    {notifications.length > 0 ? (
                      <div className="divide-y divide-white/5">
                        <AnimatePresence initial={false}>
                          {notifications.map((notif) => (
                            <motion.div
                              key={notif.id}
                              initial={{ opacity: 0, x: -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              exit={{ opacity: 0, x: 10 }}
                              className={`group cursor-pointer hover:bg-white/5 transition-all p-4 ${
                                notif.is_read === 0 ? 'bg-blue-600/5' : ''
                              }`}
                              onClick={() => handleItemClick(notif)}
                            >
                              <div className="flex gap-4">
                                <div className={`mt-1 w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border ${
                                  notif.is_read === 0 
                                    ? 'bg-blue-600/10 border-blue-600/20 text-blue-500' 
                                    : 'bg-white/5 border-white/5 text-white/20'
                                }`}>
                                  <Bell size={14} />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center justify-between gap-2 mb-1">
                                    <span className="text-[10px] font-black uppercase tracking-widest text-blue-500">
                                      Signal Detected
                                    </span>
                                    <span className="text-[9px] font-bold text-white/20 flex items-center gap-1 uppercase">
                                      <Clock size={10} />
                                      {formatTime(notif.created_at)}
                                    </span>
                                  </div>
                                  
                                  <p className={`text-xs leading-relaxed transition-colors line-clamp-2 ${
                                    notif.is_read === 0 ? 'text-white font-bold' : 'text-white/40'
                                  }`}>
                                    {notif.message.replace('🚨 REAL-TIME ALERT: ', '').replace('URGENT: ', '')}
                                  </p>

                                  <div className="mt-2 flex items-center gap-2">
                                    <div className="px-2 py-0.5 bg-white/5 rounded text-[9px] font-bold text-white/20 uppercase tracking-tighter">
                                      Lead ID: {notif.lead_id.substring(0, 8)}
                                    </div>
                                    <div className="flex-1 h-px bg-white/5" />
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
                        <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center mx-auto text-white/10">
                          <Bell size={24} />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-white/40">No notifications</p>
                          <p className="text-xs text-white/20">You're all caught up!</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Footer */}
                  {notifications.length > 0 && (
                    <div className="p-3 border-t border-white/5 bg-black/40 text-center">
                      <button 
                        onClick={() => {
                          navigate('/leads');
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
          
          <div className="h-6 w-[1px] bg-white/10 hidden md:block"></div>

          <button 
            onClick={() => navigate('/settings')}
            className="flex items-center gap-2 p-1.5 hover:bg-white/5 rounded-2xl transition-all border border-transparent hover:border-white/10 group"
            aria-label="User Profile"
          >
            <div className="w-8 h-8 bg-white/5 rounded-xl flex items-center justify-center border border-white/5 group-hover:border-blue-600/30 transition-colors">
              <User size={18} className="text-white/40" />
            </div>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
