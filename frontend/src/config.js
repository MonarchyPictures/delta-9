/**
 * 3. API CONFIGURATION (NO LOCALHOST IN PROD)
 * Environment-based configuration with fail-loud behavior.
 */
const API_URL = import.meta.env.VITE_API_URL || "";

export const getApiUrl = () => {
    return API_URL;
};

export const getApiKey = () => {
    return import.meta.env.VITE_API_KEY || "d9_prod_secret_key_2024";
};

export default getApiUrl;