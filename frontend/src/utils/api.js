// Config via Vite env vars
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const API_KEY = import.meta.env.VITE_API_KEY || "d9_prod_secret_key_2024";
export const GOOGLE_CSE_ID = "b19c2ccb43df84d2e";

export const headers = { 
  "Content-Type": "application/json", 
  "x-api-key": API_KEY 
};

export const fetchLeads = async (limit = 10) => {
  try {
    const response = await fetch(`${API_URL}/leads?limit=${limit}`, {
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
    const response = await fetch(`${API_URL}/leads?limit=${limit}`, {
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

export const searchLeads = async (query, location = "Kenya") => {
  try {
    const body = JSON.stringify({ query, location });
    const response = await fetch(`${API_URL}/search`, {
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
