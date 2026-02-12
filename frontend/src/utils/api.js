// Config via Vite env vars
export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8001";
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
      warning: data.warning || "",
    };
  } catch (error) {
    console.error("Error fetching leads:", error);
    return { leads: [], warning: "" };
  }
};

export const fetchNotifications = async () => {
  try {
    const response = await fetchWithRetry(`${API_URL}/notifications`, {
      method: "GET",
      headers,
    });
    return await response.json();
  } catch (error) {
    console.error("Error fetching notifications:", error);
    return [];
  }
};

export const markNotificationAsRead = async (id) => {
  try {
    const response = await fetchWithRetry(`${API_URL}/notifications/${id}/read`, {
      method: "POST",
      headers,
    });
    return await response.json();
  } catch (error) {
    console.error("Error marking notification as read:", error);
    return { status: "error" };
  }
};

export const clearAllNotifications = async () => {
  try {
    const response = await fetchWithRetry(`${API_URL}/notifications/clear`, {
      method: "DELETE",
      headers,
    });
    return await response.json();
  } catch (error) {
    console.error("Error clearing notifications:", error);
    return { status: "error" };
  }
};

export const searchLeads = async (query, location = "Kenya") => {
  try {
    const body = JSON.stringify({ query, location });
    const response = await fetchWithRetry(`${API_URL}/search`, {
      method: "POST",
      headers,
      body,
    });
    const data = await response.json();
    if (data.warning) {
      console.warn("⚠️ Warning from backend:", data.warning);
    }
    if (data.status === "error") {
      console.error("Search error:", data.message);
      return [];
    }
    return data.results || [];
  } catch (error) {
    console.error("Error searching leads:", error);
    return [];
  }
};

export const fetchAgents = async () => {
  try {
    const response = await fetchWithRetry(`${API_URL}/agents`, {
      method: "GET",
      headers,
    });
    return await response.json();
  } catch (error) {
    console.error("Error fetching agents:", error);
    return [];
  }
};

export const createAgent = async (agentData) => {
  try {
    const response = await fetchWithRetry(`${API_URL}/agents`, {
      method: "POST",
      headers,
      body: JSON.stringify(agentData),
    });
    return await response.json();
  } catch (error) {
    console.error("Error creating agent:", error);
    return { status: "error", message: error.message };
  }
};

export const deleteAgent = async (id) => {
  try {
    const response = await fetchWithRetry(`${API_URL}/agents/${id}`, {
      method: "DELETE",
      headers,
    });
    return await response.json();
  } catch (error) {
    console.error("Error deleting agent:", error);
    return { status: "error" };
  }
};

export const exportAgentLeads = async (id) => {
  try {
    const response = await fetchWithRetry(`${API_URL}/agents/${id}/export`, {
      method: "GET",
      headers,
    });
    
    // Get the filename from the Content-Disposition header if possible
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `agent_${id}_leads.txt`;
    if (contentDisposition && contentDisposition.indexOf('filename=') !== -1) {
      filename = contentDisposition.split('filename=')[1].replace(/"/g, '');
    }
    
    const blob = await response.blob();
    return { blob, filename };
  } catch (error) {
    console.error("Error exporting agent leads:", error);
    return null;
  }
};
