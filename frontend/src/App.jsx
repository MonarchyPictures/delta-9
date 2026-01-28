import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './views/Dashboard';
import Leads from './views/Leads';
import Agents from './views/Agents';
import Settings from './views/Settings';
import Radar from './views/Radar';
import Protocol from './views/Protocol';
import CreateAgentModal from './components/CreateAgentModal';

const App = () => {
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [notifications, setNotifications] = useState([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [agents, setAgents] = useState([]);
  const [loadingAgents, setLoadingAgents] = useState(false);

  const fetchAgents = async (isSilent = false) => {
    if (!isSilent) setLoadingAgents(true);
    
    const requestController = new AbortController();
    const timeoutId = setTimeout(() => requestController.abort(), 20000);
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/agents`, {
        signal: requestController.signal
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        setAgents(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') return;
      console.error("Fetch agents error:", err);
    } finally {
      if (!isSilent) setLoadingAgents(false);
    }
  };

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(() => fetchAgents(true), 30000);
    return () => clearInterval(interval);
  }, []);

  // Initial settings fetch from backend
  useEffect(() => {
    let isMounted = true;
    const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

    const fetchInitialSettings = async () => {
      const requestController = new AbortController();
      const timeoutId = setTimeout(() => requestController.abort(), 10000); 
      
      try {
        const res = await fetch(`${apiUrl}/settings`, {
          signal: requestController.signal
        });
        clearTimeout(timeoutId);
        if (res.ok && isMounted) {
          const data = await res.json();
          if (data) {
            if (data.notifications_enabled !== undefined) {
              setNotificationsEnabled(data.notifications_enabled);
            }
            if (data.sound_enabled !== undefined) {
              setSoundEnabled(data.sound_enabled);
            }
          }
        }
      } catch (err) {
        clearTimeout(timeoutId);
        if (err.name === 'AbortError' || !isMounted) return;
        console.error("Initial settings fetch failed:", err);
      }
    };
    fetchInitialSettings();
    return () => {
      isMounted = false;
    };
  }, []);

  // Beep sound generator
  const playBeep = () => {
    if (!notificationsEnabled || !soundEnabled) return;
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);

      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); 
      gainNode.gain.setValueAtTime(0.05, audioCtx.currentTime);

      oscillator.start();
      oscillator.stop(audioCtx.currentTime + 0.1);
    } catch (err) {
      console.error('Audio beep failed', err);
    }
  };

  // Notification Polling (Global)
  useEffect(() => {
    let isMounted = true;
    const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

    const fetchNotifications = async () => {
      const requestController = new AbortController();
      const timeoutId = setTimeout(() => requestController.abort(), 10000);

      try {
        const res = await fetch(`${apiUrl}/notifications`, {
          signal: requestController.signal
        });
        clearTimeout(timeoutId);
        if (res.ok && isMounted) {
          const data = await res.json();
          
          setNotifications(prev => {
            const unreadCount = data.filter(n => n.is_read === 0).length;
            const prevUnreadCount = prev.filter(n => n.is_read === 0).length;
            
            if (notificationsEnabled && soundEnabled && unreadCount > prevUnreadCount) {
              playBeep();
            }
            return data;
          });
        }
      } catch (err) {
        clearTimeout(timeoutId);
        if (err.name === 'AbortError' || !isMounted) return;
        console.error('Notification poll error:', err);
      }
    };

    fetchNotifications();
    const interval = setInterval(fetchNotifications, 15000); 
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [notificationsEnabled, soundEnabled]);

  const markAsRead = async (id) => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
    try {
      await fetch(`${apiUrl}/notifications/${id}/read`, { method: 'POST' });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: 1 } : n));
    } catch (err) {
      console.error("Failed to mark as read:", err);
    }
  };

  const markAllAsRead = async () => {
    const unread = notifications.filter(n => n.is_read === 0);
    for (const notif of unread) {
      markAsRead(notif.id);
    }
  };

  const clearNotifications = async () => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
    try {
      const res = await fetch(`${apiUrl}/notifications/clear`, { method: 'DELETE' });
      if (res.ok) {
        setNotifications([]);
      }
    } catch (err) {
      console.error("Failed to clear notifications:", err);
    }
  };

  const handleCreateAgent = () => {
    setIsCreateModalOpen(true);
  };

  return (
    <Router>
      <Layout 
        notifications={notifications} 
        markAsRead={markAsRead}
        markAllAsRead={markAllAsRead}
        clearNotifications={clearNotifications}
        notificationsEnabled={notificationsEnabled}
      >
        <Routes>
          <Route path="/" element={<Radar />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/agents" element={
            <Agents 
              onCreateAgent={handleCreateAgent} 
              notificationsEnabled={notificationsEnabled}
              setNotificationsEnabled={setNotificationsEnabled}
              agents={agents}
              setAgents={setAgents}
              loading={loadingAgents}
              fetchAgents={fetchAgents}
            />
          } />
          <Route path="/settings" element={
            <Settings 
              notificationsEnabled={notificationsEnabled} 
              setNotificationsEnabled={setNotificationsEnabled} 
              soundEnabled={soundEnabled}
              setSoundEnabled={setSoundEnabled}
            />
          } />
          <Route path="/protocol" element={<Protocol />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <CreateAgentModal 
          isOpen={isCreateModalOpen} 
          onClose={() => setIsCreateModalOpen(false)} 
          onSuccess={() => {
            fetchAgents();
          }}
        />
      </Layout>
    </Router>
  );
};

export default App;
