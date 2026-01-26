import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  Zap, 
  Settings, 
  Radar, 
  Bell, 
  Menu, 
  X,
  Search,
  ShieldCheck,
  User
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import NotificationDropdown from './NotificationDropdown';

const SidebarLink = ({ to, icon: Icon, label, active, onClick }) => (
  <Link
    to={to}
    onClick={onClick}
    className={`flex items-center gap-3 px-4 py-3 rounded-xl font-bold transition-all duration-200 ${
      active 
        ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' 
        : 'text-gray-400 hover:bg-white/5 hover:text-white'
    }`}
  >
    <Icon size={20} />
    <span className="text-sm uppercase tracking-wider">{label}</span>
  </Link>
);

const Layout = ({ children, notifications = [], markAsRead, markAllAsRead, notificationsEnabled }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const location = useLocation();
  const dropdownRef = useRef(null);

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Radar', href: '/', icon: Radar },
    { name: 'Live Leads', href: '/leads', icon: Zap },
    { name: 'Agents', href: '/agents', icon: Users },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  const unreadCount = notifications.filter(n => n.is_read === 0).length;

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsNotificationsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="flex h-screen bg-[#050505] overflow-hidden font-sans antialiased text-white">
      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsSidebarOpen(false)}
            className="fixed inset-0 bg-black/80 z-40 lg:hidden backdrop-blur-sm"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 bg-[#0a0a0a] border-r border-white/5 transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full p-6">
          {/* Logo */}
          <div className="flex items-center gap-3 px-2 mb-10">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-blue-600/20">
              <ShieldCheck size={24} strokeWidth={2.5} />
            </div>
            <div>
              <h1 className="text-xl font-black text-white tracking-tighter uppercase italic">
                Delta<span className="text-blue-600">9</span>
              </h1>
              <p className="text-[10px] font-bold text-white/20 uppercase tracking-widest">
                Market Intelligence
              </p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-2">
            {navigation.map((item) => (
              <SidebarLink
                key={item.name}
                to={item.href}
                icon={item.icon}
                label={item.name}
                active={location.pathname === item.href}
                onClick={() => setIsSidebarOpen(false)}
              />
            ))}
          </nav>

          {/* Footer Info */}
          <div className="mt-auto pt-6 border-t border-white/5">
            <div className="flex items-center gap-3 px-2">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-[10px] font-black text-white">
                AD
              </div>
              <div>
                <p className="text-xs font-bold text-white uppercase tracking-wider">Admin Scout</p>
                <p className="text-[10px] text-white/20 font-bold uppercase tracking-widest">Elite Operator</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-20 bg-[#0a0a0a]/50 backdrop-blur-md border-b border-white/5 px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 text-white/40 hover:text-white lg:hidden transition-colors"
            >
              <Menu size={24} />
            </button>
            <h2 className="text-sm font-black text-white/40 uppercase tracking-[0.3em]">
              {navigation.find(n => n.href === location.pathname)?.name || 'Command Center'}
            </h2>
          </div>

          <div className="flex items-center gap-4">
            {/* Search (Optional placeholder) */}
            <div className="hidden md:flex items-center gap-2 bg-white/5 border border-white/10 px-4 py-2 rounded-xl text-white/20 focus-within:border-blue-500/50 transition-all">
              <Search size={16} />
              <input 
                type="text" 
                placeholder="Global Search..." 
                className="bg-transparent border-none outline-none text-xs font-bold text-white placeholder:text-white/20 w-48"
              />
            </div>

            {/* Notifications */}
            <div className="relative" ref={dropdownRef}>
              <button 
                onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
                className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all relative ${
                  isNotificationsOpen ? 'bg-blue-600 text-white' : 'bg-white/5 text-white/40 hover:bg-white/10 hover:text-white'
                }`}
              >
                <Bell size={22} />
                {unreadCount > 0 && notificationsEnabled && (
                  <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-[10px] font-black rounded-full flex items-center justify-center border-2 border-[#0a0a0a] animate-pulse">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </button>

              <NotificationDropdown 
                notifications={notifications}
                isOpen={isNotificationsOpen}
                onClose={() => setIsNotificationsOpen(false)}
                onMarkAsRead={markAsRead}
                onMarkAllAsRead={markAllAsRead}
              />
            </div>

            {/* Profile */}
            <button className="w-12 h-12 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center text-white/40 hover:bg-white/10 hover:text-white transition-all">
              <User size={22} />
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto bg-black">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
