import React from 'react';
import { LayoutDashboard, ListFilter } from 'lucide-react';

const BottomNav = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'dashboard', label: 'Home', icon: LayoutDashboard },
    { id: 'leads', label: 'Leads', icon: ListFilter },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-surface-primary/80 border-t border-surface-secondary px-2 py-3 z-[100] backdrop-blur-xl">
      <div className="flex justify-around items-center max-w-md mx-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex flex-col items-center justify-center min-w-[64px] h-12 gap-1.5 transition-all active:scale-90 touch-none select-none ${
                isActive ? 'text-brand-primary' : 'text-text-tertiary'
              }`}
            >
              <div className={`p-2 rounded-xl transition-all duration-300 ${isActive ? 'bg-brand-primary/10 scale-110' : ''}`}>
                <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
              </div>
              <span className={`text-[8px] font-bold uppercase tracking-[0.15em] transition-opacity duration-300 ${isActive ? 'opacity-100' : 'opacity-60'}`}>
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
      {/* Safe area for mobile home indicators */}
      <div className="h-4 md:hidden" />
    </nav>
  );
};

export default BottomNav;
