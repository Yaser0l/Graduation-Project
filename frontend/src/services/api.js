const RAW_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api').replace(/\/+$/, '');
const BASE_URL = RAW_API_BASE_URL.endsWith('/api') ? RAW_API_BASE_URL : `${RAW_API_BASE_URL}/api`;
export const EVENTS_BASE_URL = BASE_URL.replace(/\/api$/, '');

const getHeaders = (isFormData = false) => {
  const token = localStorage.getItem('token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  return headers;
};

const handleResponse = async (response) => {
  if (!response.ok) {
    let errorBody;
    try {
      errorBody = await response.json();
    } catch {
      errorBody = { detail: 'Unknown network or server error' };
    }
    throw new Error(errorBody.detail || `HTTP error! status: ${response.status}`);
  }
  return response.json();
};

const fetchWithTimeout = async (resource, options = {}) => {
  const { timeout = 30000 } = options; // Default 30s timeout

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(resource, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    if (error.name === 'AbortError') {
      throw new Error(`Request timed out after ${timeout / 1000} seconds`);
    }
    throw new Error(`Network error: ${error.message}`);
  }
};

export const api = {
  auth: {
    login: async (email, password) => {
      // The backend expects OAuth2PasswordRequestForm (form-data)
      const formData = new URLSearchParams();
      formData.append('username', email); // backend uses 'username' for the email field
      formData.append('password', password);

      const response = await fetchWithTimeout(`${BASE_URL}/auth/login`, {
        method: 'POST',
        headers: getHeaders(true),
        body: formData,
      });
      return handleResponse(response);
    },
    register: async (name, email, password) => {
      const response = await fetchWithTimeout(`${BASE_URL}/auth/register`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ name, email, password }),
      });
      return handleResponse(response);
    },
  },

  vehicles: {
    list: async () => {
      const response = await fetchWithTimeout(`${BASE_URL}/vehicles/`, {
        method: 'GET',
        headers: getHeaders(),
      });
      return handleResponse(response);
    },
    create: async (vehicleData) => {
      const response = await fetchWithTimeout(`${BASE_URL}/vehicles/`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(vehicleData),
      });
      return handleResponse(response);
    },
    update: async (vehicleId, updateData) => {
      const response = await fetchWithTimeout(`${BASE_URL}/vehicles/${vehicleId}`, {
        method: 'PATCH',
        headers: getHeaders(),
        body: JSON.stringify(updateData),
      });
      return handleResponse(response);
    },
    remove: async (vehicleId) => {
      const response = await fetchWithTimeout(`${BASE_URL}/vehicles/${vehicleId}`, {
        method: 'DELETE',
        headers: getHeaders(),
      });

      if (response.status === 204) {
        return null;
      }

      return handleResponse(response);
    },
  },

  diagnostics: {
    list: async () => {
      const response = await fetchWithTimeout(`${BASE_URL}/diagnostics/`, {
        method: 'GET',
        headers: getHeaders(),
      });
      return handleResponse(response);
    },
    listByVehicle: async (vehicleId) => {
      const response = await fetchWithTimeout(`${BASE_URL}/diagnostics/vehicle/${vehicleId}`, {
        method: 'GET',
        headers: getHeaders(),
      });
      return handleResponse(response);
    },
    get: async (reportId) => {
      const response = await fetchWithTimeout(`${BASE_URL}/diagnostics/${reportId}`, {
        method: 'GET',
        headers: getHeaders(),
      });
      return handleResponse(response);
    },
    resolve: async (reportId) => {
      const response = await fetchWithTimeout(`${BASE_URL}/diagnostics/${reportId}/resolve`, {
        method: 'PATCH',
        headers: getHeaders(),
      });
      return handleResponse(response);
    },
    fullReport: async (reportId, language = 'en') => {
      const response = await fetchWithTimeout(`${BASE_URL}/diagnostics/${reportId}/full-report`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ language }),
        timeout: 300000,
      });
      return handleResponse(response);
    },
  },

  maintenance: {
    listByVehicle: async (vehicleId) => {
      const response = await fetchWithTimeout(`${BASE_URL}/maintenance/vehicle/${vehicleId}`, {
        method: 'GET',
        headers: getHeaders(),
      });
      return handleResponse(response);
    },
    completeTask: async (vehicleId, taskId, notes = null) => {
      const response = await fetchWithTimeout(`${BASE_URL}/maintenance/vehicle/${vehicleId}/tasks/${taskId}/complete`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ notes }),
      });
      return handleResponse(response);
    },
  },

  chat: {
    send: async (reportId, message) => {
      const response = await fetchWithTimeout(`${BASE_URL}/chat/${reportId}`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ message }),
      });
      return handleResponse(response);
    },
    history: async (reportId) => {
      const response = await fetchWithTimeout(`${BASE_URL}/chat/${reportId}/history`, {
        method: 'GET',
        headers: getHeaders(),
      });
      return handleResponse(response);
    },
  },
};
