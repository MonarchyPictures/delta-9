/**
 * 3. API CONFIGURATION (NO LOCALHOST IN PROD)
 * Environment-based configuration with fail-loud behavior.
 */
const API_URL = import.meta.env.VITE_API_URL;

export const getApiUrl = () => {
    // Fail loudly if API base URL is missing in production environment
    if (!API_URL) {
        if (import.meta.env.PROD) {
            const errorMsg = "FATAL ERROR: VITE_API_URL is missing in production environment. Deployment aborted.";
            console.error(errorMsg);
            throw new Error(errorMsg);
        }
        // Fallback for local development only if not in PROD mode
        // Using relative path to leverage Vite proxy
        return "/api"; 
    }
    return API_URL;
};

export const getApiKey = () => {
    return import.meta.env.VITE_API_KEY || "d9_prod_secret_key_2024";
};

export default getApiUrl;