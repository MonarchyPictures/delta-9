import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, List, Users, Settings as SettingsIcon } from 'lucide-react';
import Header from './Header';

const Layout = ({ children, notifications, markAsRead, markAllAsRead, clearNotifications, notificationsEnabled, setNotificationsEnabled }) => {
  return (
    <div className="flex h-screen bg-black text-white font-sans overflow-hidden">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex flex-col w-64 border-r border-white/10 bg-black/50 backdrop-blur-xl">
        <div className="p-8">
           <h1 className="text-2xl font-black italic tracking-tighter">DELTA<span className="text-blue-600">9</span></h1>
        </div>
        
        <nav className="flex-1 px-4 space-y-2">
          <NavLink to="/" className={({ isActive }) => `flex items-center gap-4 px-4 py-3 rounded-xl transition-all ${isActive ? 'bg-blue-600 text-white shadow-lg' : 'text-white/40 hover:bg-white/5 hover:text-white'}`}>
            <Home size={20} /> <span className="font-bold text-sm">Vehicle Dashboard</span>
          </NavLink>
          <NavLink to="/leads" className={({ isActive }) => `flex items-center gap-4 px-4 py-3 rounded-xl transition-all ${isActive ? 'bg-blue-600 text-white shadow-lg' : 'text-white/40 hover:bg-white/5 hover:text-white'}`}>
            <List size={20} /> <span className="font-bold text-sm">Live Signals</span>
          </NavLink>
          {/* Agents hidden in Vehicle-Only Mode */}
          {/* <NavLink to="/agents" className={({ isActive }) => `flex items-center gap-4 px-4 py-3 rounded-xl transition-all ${isActive ? 'bg-blue-600 text-white shadow-lg' : 'text-white/40 hover:bg-white/5 hover:text-white'}`}>
            <Users size={20} /> <span className="font-bold text-sm">Agents</span>
          </NavLink> */}
        </nav>

        <div className="p-4">
          <NavLink to="/settings" className={({ isActive }) => `flex items-center gap-4 px-4 py-3 rounded-xl transition-all ${isActive ? 'bg-blue-600 text-white shadow-lg' : 'text-white/40 hover:bg-white/5 hover:text-white'}`}>
            <SettingsIcon size={20} /> <span className="font-bold text-sm">Settings</span>
          </NavLink>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col relative overflow-hidden">
        <Header 
          notifications={notifications} 
          markAsRead={markAsRead} 
          markAllAsRead={markAllAsRead} 
          clearNotifications={clearNotifications}
          notificationsEnabled={notificationsEnabled}
          setNotificationsEnabled={setNotificationsEnabled}
        />
        <main className="flex-1 flex flex-col overflow-hidden relative">
          {children}
        </main>

        {/* Bottom Nav - Mobile Only */}
        <nav className="md:hidden flex items-center justify-around p-4 border-t border-white/10 bg-black/80 backdrop-blur-xl">
          <NavLink to="/" className={({ isActive }) => `${isActive ? 'text-blue-500' : 'text-white/40'}`}><Home /></NavLink>
          <NavLink to="/leads" className={({ isActive }) => `${isActive ? 'text-blue-500' : 'text-white/40'}`}><List /></NavLink>
          {/* <NavLink to="/agents" className={({ isActive }) => `${isActive ? 'text-blue-500' : 'text-white/40'}`}><Users /></NavLink> */}
          <NavLink to="/settings" className={({ isActive }) => `${isActive ? 'text-blue-500' : 'text-white/40'}`}><SettingsIcon /></NavLink>
        </nav>
      </div>
    </div>
  );
};

export default Layout;