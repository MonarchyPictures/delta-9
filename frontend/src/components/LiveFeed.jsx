import React, { useState, useEffect, useRef } from 'react';
import LiveFeedItem from './LiveFeedItem';
import { motion, AnimatePresence } from 'framer-motion';

const LiveFeed = ({ leads: initialLeads }) => {
  const [leads, setLeads] = useState(initialLeads);
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  const scrollRef = useRef(null);
  const lastScrollTop = useRef(0);

  // Update leads when prop changes
  useEffect(() => {
    setLeads(initialLeads);
  }, [initialLeads]);

  // Handle auto-scroll
  useEffect(() => {
    if (isAutoScroll && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }
  }, [leads, isAutoScroll]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    
    const { scrollTop } = scrollRef.current;
    
    // If user scrolls down, disable auto-scroll
    if (scrollTop > 10 && isAutoScroll) {
      setIsAutoScroll(false);
    } 
    // If user scrolls back to top, re-enable auto-scroll
    else if (scrollTop <= 2 && !isAutoScroll) {
      setIsAutoScroll(true);
    }
    
    lastScrollTop.current = scrollTop;
  };

  return (
    <div className="flex-1 h-full overflow-hidden flex flex-col bg-white border border-gray-100 rounded-2xl shadow-sm">
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-50 bg-white/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Live Intelligence Stream</h3>
          {isAutoScroll && (
            <div className="flex items-center gap-2 px-2.5 py-1 bg-blue-50 rounded-full border border-blue-100">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-blue-600"></span>
              </span>
              <span className="text-[9px] font-bold text-blue-600 uppercase tracking-widest">Auto-Sync</span>
            </div>
          )}
        </div>
        
        {!isAutoScroll && (
          <button 
            onClick={() => setIsAutoScroll(true)}
            className="text-[10px] font-bold text-gray-500 hover:text-blue-600 uppercase tracking-widest transition-all flex items-center gap-2 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100 hover:border-blue-200"
          >
            <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse" />
            Resume Feed
          </button>
        )}
      </div>
      
      <div 
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto divide-y divide-gray-50 no-scrollbar"
      >
        <AnimatePresence initial={false}>
          {leads.map((lead, index) => (
            <motion.div
              key={lead.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.3 }}
            >
              <LiveFeedItem 
                lead={lead} 
                isNew={index === 0 && leads.length > initialLeads.length} 
              />
            </motion.div>
          ))}
        </AnimatePresence>
        
        {leads.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center py-32 opacity-50">
            <div className="w-10 h-10 border-2 border-dashed border-blue-200 rounded-full animate-spin mb-4" />
            <div className="space-y-1 text-center">
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Patrolling Platforms</p>
              <p className="text-xs font-medium text-gray-300">Awaiting encrypted signals...</p>
            </div>
          </div>
        )}
      </div>

      <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex -space-x-2">
            {[1,2,3].map(i => (
              <div key={i} className="w-6 h-6 rounded-lg border-2 border-white bg-gray-900 flex items-center justify-center text-[8px] font-bold text-blue-400">
                AI
              </div>
            ))}
          </div>
          <div className="space-y-0.5">
            <span className="block text-[8px] text-gray-400 font-bold uppercase tracking-widest">Cluster Status</span>
            <span className="block text-[9px] text-gray-600 font-bold">3 Active Nodes</span>
          </div>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-[8px] text-gray-400 font-bold uppercase tracking-widest">Efficiency</span>
          <span className="text-[9px] text-green-600 font-bold uppercase tracking-widest flex items-center gap-1">
            <div className="w-1 h-1 bg-green-500 rounded-full animate-pulse" />
            94.2%
          </span>
        </div>
      </div>
    </div>
  );
};

export default LiveFeed;
