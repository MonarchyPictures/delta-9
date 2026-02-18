// Config via Vite env vars
export const API_URL = import.meta.env.VITE_API_URL || "";
export const API_KEY = import.meta.env.VITE_API_KEY || "d9_prod_secret_key_2024";
export const GOOGLE_CSE_ID = "f32db13486dc14c26";

export const headers = { 
  "Content-Type": "application/json", 
  "Accept": "application/json",
  "x-api-key": API_KEY 
};

// Helper for retries with exponential backoff
const fetchWithRetry = async (url, options = {}, retries = 3, backoff = 1000) => {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      if (retries > 0 && (response.status >= 500 || response.status === 404)) {
        // Retry for server errors or temporary 404s (e.g. during startup)
        await new Promise(resolve => setTimeout(resolve, backoff));
        return fetchWithRetry(url, options, retries - 1, backoff * 2);
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response;
  } catch (error) {
    if (retries > 0) {
      console.warn(`Fetch failed, retrying in ${backoff}ms...`, error);
      await new Promise(resolve => setTimeout(resolve, backoff));
      return fetchWithRetry(url, options, retries - 1, backoff * 2);
    }
    throw error;
  }
};

export const fetchLeads = async (limit = 10) => {
  try {
    const response = await fetchWithRetry(`${API_URL}/leads?limit=${limit}`, {
      method: "GET",
      headers,
    });
    const data = await response.json();
    if (data.warning) {
      console.warn("⚠️ Warning from backend:", data.warning);
    }
    return data.leads || [];
  } catch (error) {
    console.error("Error fetching leads:", error);
    return [];
  }
};

export const fetchLeadsMeta = async (limit = 10) => {
    try {
      const response = await fetchWithRetry(`${API_URL}/leads?limit=${limit}`, {
        method: "GET",
        headers,
      });
      const data = await response.json();
      return {
          leads: data.leads || [],
          warning: data.warning
      };
    } catch (error) {
      console.error("Error fetching leads meta:", error);
      return { leads: [], warning: "" };
    }
};

export const fetchNotifications = async () => {
    try {
        const response = await fetchWithRetry(`${API_URL}/notifications/`, {
            method: "GET",
            headers
        });
        if (!response.ok) throw new Error("Failed to fetch notifications");
        return await response.json();
    } catch (error) {
        console.error("Error fetching notifications:", error);
        return [];
    }
};

export const fetchNotificationCount = async (unreadOnly = false) => {
    try {
        const response = await fetchWithRetry(`${API_URL}/notifications/count?unread_only=${unreadOnly}`, {
            method: "GET",
            headers
        });
        if (!response.ok) throw new Error("Failed to fetch notification count");
        const data = await response.json();
        return data.count || 0;
    } catch (error) {
        console.error("Error fetching notification count:", error);
        return 0;
    }
};

export const markNotificationAsRead = async (id) => {
    try {
        await fetch(`${API_URL}/notifications/${id}/read`, {
            method: "POST",
            headers
        });
    } catch (error) {
        console.error("Error marking notification as read:", error);
    }
};

export const clearAllNotifications = async () => {
    try {
        await fetch(`${API_URL}/notifications/`, {
            method: "DELETE",
            headers
        });
    } catch (error) {
        console.error("Error clearing notifications:", error);
    }
};

// --- AGENTS API ---

export const fetchAgents = async () => {
    try {
        const response = await fetchWithRetry(`${API_URL}/agents/`, {
            method: "GET",
            headers
        });
        if (!response.ok) throw new Error("Failed to fetch agents");
        return await response.json();
    } catch (error) {
        console.error("Error fetching agents:", error);
        return [];
    }
};

export const createAgent = async (agentData) => {
    try {
        const response = await fetchWithRetry(`${API_URL}/agents/`, {
            method: "POST",
            headers,
            body: JSON.stringify(agentData)
        });
        if (!response.ok) throw new Error("Failed to create agent");
        return await response.json();
    } catch (error) {
        console.error("Error creating agent:", error);
        return { error: error.message };
    }
};

export const stopAgent = async (id) => {
    try {
        const response = await fetch(`${API_URL}/agents/${id}/stop`, {
            method: "POST",
            headers
        });
        if (!response.ok) throw new Error("Failed to stop agent");
        return await response.json();
    } catch (error) {
        console.error("Error stopping agent:", error);
        return { error: error.message };
    }
};

export const deleteAgent = async (id) => {
    try {
        const response = await fetch(`${API_URL}/agents/${id}`, {
            method: "DELETE",
            headers
        });
        if (!response.ok) throw new Error("Failed to delete agent");
        return await response.json();
    } catch (error) {
        console.error("Error deleting agent:", error);
        return { error: error.message };
    }
};

export const exportAgentLeads = async (id) => {
    try {
        const response = await fetch(`${API_URL}/agents/${id}/export`, {
            method: "GET",
            headers
        });
        
        if (!response.ok) throw new Error("Failed to export leads");
        
        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `agent_${id}_leads.txt`;
        
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="?([^"]+)"?/);
            if (match && match[1]) {
                filename = match[1];
            }
        }
        
        return { blob, filename };
    } catch (error) {
        console.error("Error exporting agent leads:", error);
        return null;
    }
};

export const fetchAgentLeads = async (agentId, limit = 50, offset = 0) => {
    try {
        const response = await fetchWithRetry(`${API_URL}/agents/${agentId}/leads?limit=${limit}&offset=${offset}`, {
            method: "GET",
            headers
        });
        if (!response.ok) throw new Error("Failed to fetch agent leads");
        return await response.json();
    } catch (error) {
        console.error("Error fetching agent leads:", error);
        return [];
    }
};
