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
        return "http://localhost:8080"; 
    }
    return API_URL;
};

export const getApiKey = () => {
    return import.meta.env.VITE_API_KEY || "";
};

export default getApiUrl;