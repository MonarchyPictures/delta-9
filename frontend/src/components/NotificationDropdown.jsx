import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Bell, X, Check, Clock, Trash2, ExternalLink, Zap } from 'lucide-react';

const NotificationDropdown = ({ 
  notifications, 
  onClose, 
  onMarkAsRead, 
  onMarkAllAsRead,
  isOpen 
}) => {
  const navigate = useNavigate();
  const unreadCount = notifications.filter(n => n.is_read === 0).length;

  const handleNotificationClick = (notif) => {
    onMarkAsRead(notif.id);
    if (notif.lead_id) {
      navigate(`/leads?lead_id=${notif.lead_id}`);
      onClose();
    }
  };

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

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: 10, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.95 }}
          className="absolute right-0 mt-4 w-96 bg-[#111] border border-white/10 rounded-2xl shadow-2xl z-[100] overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-white/5 bg-white/5">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Intelligence Feed</h3>
              {unreadCount > 0 && (
                <span className="px-1.5 py-0.5 bg-blue-600 text-white text-[10px] font-black rounded-md">
                  {unreadCount} NEW
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button 
                  onClick={onMarkAllAsRead}
                  className="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-blue-500"
                  title="Mark all as read"
                >
                  <Check size={16} />
                </button>
              )}
              <button 
                onClick={onClose}
                className="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* List */}
          <div className="max-h-[400px] overflow-y-auto custom-scrollbar">
            {notifications.length > 0 ? (
              <div className="divide-y divide-white/5">
                {notifications.map((notif) => (
                  <div 
                    key={notif.id}
                    className={`p-4 hover:bg-white/5 transition-colors cursor-pointer group relative ${notif.is_read === 0 ? 'bg-blue-500/5' : ''}`}
                    onClick={() => handleNotificationClick(notif)}
                  >
                    <div className="flex gap-3">
                      <div className={`mt-1 w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${notif.is_read === 0 ? 'bg-blue-600/20 text-blue-500' : 'bg-white/5 text-white/20'}`}>
                        <Zap size={14} fill={notif.is_read === 0 ? 'currentColor' : 'none'} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm leading-relaxed mb-1 ${notif.is_read === 0 ? 'text-white font-medium' : 'text-white/50'}`}>
                          {notif.message}
                        </p>
                        <div className="flex items-center gap-3">
                          <span className="text-[10px] text-white/20 font-bold uppercase tracking-wider flex items-center gap-1">
                            <Clock size={10} />
                            {formatTime(notif.created_at)}
                          </span>
                          {notif.is_read === 0 && (
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
                          )}
                        </div>
                      </div>
                      <button 
                        className="opacity-0 group-hover:opacity-100 p-2 hover:bg-white/10 rounded-lg transition-all text-white/40"
                        title="View Intelligence"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleNotificationClick(notif);
                        }}
                      >
                        <ExternalLink size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 flex flex-col items-center justify-center text-center px-6">
                <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center text-white/10 mb-4">
                  <Bell size={24} />
                </div>
                <h4 className="text-white font-bold mb-1 uppercase tracking-wider text-sm">Silent Sector</h4>
                <p className="text-white/20 text-xs">No active intelligence pings detected in this sector.</p>
              </div>
            )}
          </div>

          {/* Footer */}
          {notifications.length > 0 && (
            <div className="p-3 border-t border-white/5 bg-white/5 text-center">
              <button 
                onClick={onClose}
                className="text-[10px] font-black text-white/30 uppercase tracking-[0.2em] hover:text-white transition-colors"
              >
                Dismiss Feed
              </button>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default NotificationDropdown;