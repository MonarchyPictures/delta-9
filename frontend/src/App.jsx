import getApiUrl, { getApiKey } from './config';
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './views/Dashboard';
import Leads from './views/Leads';
import Agents from './views/Agents';
import Settings from './views/Settings';
import CreateAgentModal from './components/CreateAgentModal';

const App = () => {
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [notifications, setNotifications] = useState([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [agents, setAgents] = useState([]);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const agentsControllerRef = React.useRef(null);

  const fetchAgents = async (isSilent = false) => {
    // Skip if a request is already in progress to avoid console noise from aborts
    if (agentsControllerRef.current) {
      // If it's a silent request and one is already running, just skip
      if (isSilent) return;
      // If it's a foreground request, we'll let the existing one finish rather than aborting it
      // unless it's been running for too long.
      return; 
    }

    if (!isSilent) setLoadingAgents(true);
    
    const controller = new AbortController();
    agentsControllerRef.current = controller;
    const timeoutId = setTimeout(() => {
      if (agentsControllerRef.current === controller) {
        controller.abort();
      }
    }, 20000);
    
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      const res = await fetch(`${apiUrl}/agents`, {
        signal: controller.signal,
        headers: {
          'X-API-Key': apiKey
        }
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        setAgents(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      clearTimeout(timeoutId);
      // AbortError is expected, don't log it
      if (err.name === 'AbortError') return;
      if (!isSilent) console.error("Fetch agents error:", err);
    } finally {
      if (!isSilent) setLoadingAgents(false);
      if (agentsControllerRef.current === controller) {
        agentsControllerRef.current = null;
      }
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
    const apiUrl = getApiUrl();
    const apiKey = getApiKey();

    const fetchInitialSettings = async () => {
      const requestController = new AbortController();
      const timeoutId = setTimeout(() => requestController.abort(), 10000); 
      
      try {
        const res = await fetch(`${apiUrl}/settings`, {
          signal: requestController.signal,
          headers: {
            'X-API-Key': apiKey
          }
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
    const apiUrl = getApiUrl();
    const apiKey = getApiKey();
    let pollTimer = null;
    const activeControllerRef = { current: null };

    const fetchNotifications = async () => {
      // If a request is already in progress or component unmounted, skip this poll cycle
      if (activeControllerRef.current || !isMounted) return;
      
      const controller = new AbortController();
      activeControllerRef.current = controller;
      
      // Use a robust timeout for high-latency environments (increased to 100s)
      const timeoutId = setTimeout(() => {
        if (activeControllerRef.current === controller) {
          controller.abort();
        }
      }, 100000); 

      try {
        const res = await fetch(`${apiUrl}/notifications`, {
          signal: controller.signal,
          headers: { 
            'X-API-Key': apiKey,
            'Cache-Control': 'no-cache'
          }
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
        // ABSOLUTELY SILENT on AbortError to prevent console clutter in dev environment
        if (err.name === 'AbortError') return;
        
        if (isMounted) {
          // Only log real errors, not cancellations
          console.debug("Notification poll skipped or failed:", err.message);
        }
      } finally {
        if (activeControllerRef.current === controller) {
          activeControllerRef.current = null;
        }
        // Schedule next poll ONLY after the previous one is fully complete (success or fail)
        if (isMounted) {
          pollTimer = setTimeout(fetchNotifications, 60000); // Poll every 60s
        }
      }
    };

    fetchNotifications();

    return () => {
      isMounted = false;
      if (pollTimer) clearTimeout(pollTimer);
      if (activeControllerRef.current) {
        activeControllerRef.current.abort();
        activeControllerRef.current = null;
      }
    };
  }, [notificationsEnabled, soundEnabled]);

  const markAsRead = async (id) => {
    const apiUrl = getApiUrl();
    const apiKey = getApiKey();
    try {
      await fetch(`${apiUrl}/notifications/${id}/read`, { 
        method: 'POST',
        headers: {
          'X-API-Key': apiKey
        }
      });
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
    const apiUrl = getApiUrl();
    const apiKey = getApiKey();
    try {
      const res = await fetch(`${apiUrl}/notifications/clear`, { 
        method: 'DELETE',
        headers: {
          'X-API-Key': apiKey
        }
      });
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
        setNotificationsEnabled={setNotificationsEnabled}
      >
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/leads" element={<Leads />} />
          <Route path="/agents" element={
            <Agents 
              onCreateAgent={handleCreateAgent} 
              agents={agents}
              loading={loadingAgents}
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
          {/* Protocol hidden for prod */}
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