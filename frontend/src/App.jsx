import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './views/Dashboard';
import Leads from './views/Leads';
import Agents from './views/Agents';
import Settings from './views/Settings';
import Radar from './views/Radar';

const App = () => {
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [notifications, setNotifications] = useState([]);

  // Initial settings fetch from backend
  useEffect(() => {
    const controller = new AbortController();
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const fetchInitialSettings = async () => {
      const timeoutId = setTimeout(() => controller.abort(), 15000); 
      try {
        const res = await fetch(`${apiUrl}/settings`, {
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (res.ok) {
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
        if (err.name === 'AbortError' || err.message?.includes('aborted')) return;
        console.error("Initial settings fetch failed:", err);
      }
    };
    fetchInitialSettings();
    return () => controller.abort();
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
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const fetchNotifications = async () => {
      if (!notificationsEnabled) return;
      try {
        const res = await fetch(`${apiUrl}/notifications`);
        if (res.ok) {
          const data = await res.json();
          
          // Check for new notifications to play sound
          setNotifications(prev => {
            const unreadCount = data.filter(n => n.is_read === 0).length;
            const prevUnreadCount = prev.filter(n => n.is_read === 0).length;
            
            if (unreadCount > prevUnreadCount) {
              playBeep();
            }
            return data;
          });
        }
      } catch (err) {
        console.error('Notification poll error:', err);
      }
    };

    fetchNotifications();
    const interval = setInterval(fetchNotifications, 10000); 
    return () => clearInterval(interval);
  }, [notificationsEnabled, soundEnabled]);

  const markAsRead = async (id) => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
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

  return (
    <Router>
      <Layout 
        notifications={notifications} 
        markAsRead={markAsRead}
        markAllAsRead={markAllAsRead}
        notificationsEnabled={notificationsEnabled}
      >
        <Routes>
          <Route path="/" element={<Radar />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/settings" element={
            <Settings 
              notificationsEnabled={notificationsEnabled} 
              setNotificationsEnabled={setNotificationsEnabled} 
              soundEnabled={soundEnabled}
              setSoundEnabled={setSoundEnabled}
            />
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;
