import React, { useState, useEffect } from 'react';
import { User, Search, X, Bell } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import NotificationDropdown from './NotificationDropdown';
import { fetchNotifications, markNotificationAsRead, clearAllNotifications } from '../utils/api';

const Header = () => {
  const [showMobileSearch, setShowMobileSearch] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [notifications, setNotifications] = useState([]);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadNotifications();
    const interval = setInterval(loadNotifications, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadNotifications = async () => {
    const data = await fetchNotifications();
    setNotifications(data || []);
  };

  const handleMarkAsRead = async (id) => {
    await markNotificationAsRead(id);
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: 1 } : n));
  };

  const handleMarkAllAsRead = async () => {
    const unread = notifications.filter(n => n.is_read === 0);
    await Promise.all(unread.map(n => markNotificationAsRead(n.id)));
    setNotifications(prev => prev.map(n => ({ ...n, is_read: 1 })));
  };

  const handleClearAll = async () => {
    await clearAllNotifications();
    setNotifications([]);
  };

  const unreadCount = notifications.filter(n => n.is_read === 0).length;
  
  const handleSearch = (e) => {
    if (e.key === 'Enter' && searchQuery.trim()) {
      navigate(`/?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchQuery('');
      setShowMobileSearch(false);
    }
  };

  return (
    <header className="h-16 bg-black/50 backdrop-blur-md border-b border-white/10 z-[100] px-4 md:px-8">
      <div className="max-w-7xl mx-auto h-full flex items-center justify-between relative">
        {/* Branding/Section Title */}
        <div className="flex items-center gap-4">
          <div className="md:hidden flex items-center gap-2" onClick={() => navigate('/')}>
             <h1 className="text-xl font-black italic tracking-tighter cursor-pointer">D<span className="text-blue-600">9</span></h1>
          </div>
          <div className="hidden md:block">
            <span className="text-white/40 text-[10px] font-black uppercase tracking-[0.2em]">Market Intelligence Node</span>
          </div>
        </div>

        {/* Global Search Bar */}
        <div className={`flex-1 max-w-md mx-4 md:mx-8 relative group ${showMobileSearch ? 'flex absolute inset-x-0 top-0 h-full bg-black z-50 items-center px-4' : 'hidden md:flex'}`}>
          <Search className="absolute left-8 md:left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-white/20 group-focus-within:text-blue-500 transition-colors" />
          <input
            type="text"
            autoFocus={showMobileSearch}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleSearch}
            onBlur={() => {
              if (showMobileSearch && !searchQuery) setShowMobileSearch(false);
            }}
            placeholder="Search buyers in Kenya..."
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-16 md:pl-11 pr-12 md:pr-4 py-2 text-sm text-white outline-none focus:border-blue-500/50 focus:bg-white/10 transition-all font-bold italic placeholder:text-white/10"
          />
          {showMobileSearch && (
            <button 
              onClick={() => setShowMobileSearch(false)}
              className="absolute right-8 text-white/40 hover:text-white"
            >
              <X size={20} />
            </button>
          )}
        </div>

        {/* User Menu Right */}
        <div className="flex items-center gap-3 md:gap-5">
          {/* Mobile Search Toggle */}
          <button 
            onClick={() => setShowMobileSearch(true)}
            className="md:hidden p-2.5 rounded-xl text-white/40 hover:text-blue-600 hover:bg-blue-600/10 transition-all"
          >
            <Search size={20} />
          </button>
          
          <div className="h-6 w-[1px] bg-white/10 hidden md:block"></div>

          {/* Notifications */}
          <div className="relative">
            <button 
              onClick={() => setIsNotifOpen(!isNotifOpen)}
              className="relative p-2.5 rounded-xl text-white/40 hover:text-blue-600 hover:bg-blue-600/10 transition-all group"
              aria-label="Notifications"
            >
              <Bell size={20} className="group-hover:scale-110 transition-transform" />
              {unreadCount > 0 && (
                <span className="absolute top-2 right-2 w-4 h-4 bg-red-600 text-white text-[10px] font-black rounded-full flex items-center justify-center border-2 border-black animate-pulse">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            <NotificationDropdown 
              isOpen={isNotifOpen}
              notifications={notifications}
              onClose={() => setIsNotifOpen(false)}
              onMarkAsRead={handleMarkAsRead}
              onMarkAllAsRead={handleMarkAllAsRead}
              onClearAll={handleClearAll}
            />
          </div>
          
          <div className="h-6 w-[1px] bg-white/10 hidden md:block"></div>

          <button 
            onClick={() => navigate('/settings')}
            className="flex items-center gap-2 p-1.5 hover:bg-white/5 rounded-2xl transition-all border border-transparent hover:border-white/10 group"
            aria-label="Settings"
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
