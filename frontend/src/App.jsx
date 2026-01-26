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

  // Initial settings fetch from backend
  useEffect(() => {
    const controller = new AbortController();
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const fetchInitialSettings = async () => {
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      try {
        const res = await fetch(`${apiUrl}/settings`, {
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          const data = await res.json();
          if (data && data.notifications_enabled !== undefined) {
            setNotificationsEnabled(data.notifications_enabled);
          }
        }
      } catch (err) {
        clearTimeout(timeoutId);
        if (err.name !== 'AbortError') {
          console.error("Initial settings fetch failed:", err);
        }
      }
    };
    fetchInitialSettings();
    return () => controller.abort();
  }, []);

  // Beep sound generator
  const playBeep = () => {
    if (!notificationsEnabled) return;
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);

      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
      gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);

      oscillator.start();
      oscillator.stop(audioCtx.currentTime + 0.1);
    } catch (err) {
      console.error('Audio beep failed', err);
    }
  };

  // Notification Polling (Global)
  useEffect(() => {
    const controller = new AbortController();
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const pollNotifications = async (signal) => {
      if (!notificationsEnabled) return;
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      try {
        const res = await fetch(`${apiUrl}/notifications`, {
          signal: signal
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          const newNotifs = await res.json();
          if (newNotifs.length > 0) {
            playBeep();
            
            for (const notif of newNotifs) {
              const markController = new AbortController();
              const markTimeoutId = setTimeout(() => markController.abort(), 3000);
              try {
                await fetch(`${apiUrl}/notifications/${notif.id}/read`, { 
                  method: 'POST',
                  signal: markController.signal
                });
                clearTimeout(markTimeoutId);
              } catch (e) {
                clearTimeout(markTimeoutId);
                console.error("Failed to mark notification as read:", e);
              }
            }
          }
        }
      } catch (err) {
        clearTimeout(timeoutId);
        if (err.name !== 'AbortError') {
          console.error('Notification poll error:', err);
        }
      }
    };

    const interval = setInterval(() => {
      const intervalController = new AbortController();
      pollNotifications(intervalController.signal);
    }, 10000); // Poll every 10s
    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, [notificationsEnabled]);

  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/settings" element={<Settings notificationsEnabled={notificationsEnabled} setNotificationsEnabled={setNotificationsEnabled} />} />
          <Route path="/radar" element={<Radar />} />
          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;
