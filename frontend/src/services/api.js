const BASE_URL = 'http://localhost:5000/api';

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
    const errorBody = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(errorBody.detail || `HTTP error! status: ${response.status}`);
  }
  return response.json();
};

export const api = {
  auth: {
    login: async (email, password) => {
      // The backend expects OAuth2PasswordRequestForm (form-data)
      const formData = new URLSearchParams();
      formData.append('username', email); // backend uses 'username' for the email field
      formData.append('password', password);

      const response = await fetch(`${BASE_URL}/auth/login`, {
        method: 'POST',
        headers: getHeaders(true),
        body: formData,
      });
      return handleResponse(response);
    },
    register: async (name, email, password) => {
      const response = await fetch(`${BASE_URL}/auth/register`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ name, email, password }),
      });
      return handleResponse(response);
    },
  },

  vehicles: {
    list: async () => {
      const response = await fetch(`${BASE_URL}/vehicles/`, {
        method: 'GET',
        headers: getHeaders(),
      });
      return handleResponse(response);
    },
    create: async (vehicleData) => {
      const response = await fetch(`${BASE_URL}/vehicles/`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(vehicleData),
      });
      return handleResponse(response);
    },
  },

  diagnostics: {
    list: async () => {
      const response = await fetch(`${BASE_URL}/diagnostics/`, {
        method: 'GET',
        headers: getHeaders(),
      });
      return handleResponse(response);
    },
    get: async (reportId) => {
      const response = await fetch(`${BASE_URL}/diagnostics/${reportId}`, {
        method: 'GET',
        headers: getHeaders(),
      });
      return handleResponse(response);
    },
  },

  chat: {
    send: async (reportId, message) => {
      const response = await fetch(`${BASE_URL}/chat/${reportId}`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ message }),
      });
      return handleResponse(response);
    },
    history: async (reportId) => {
      const response = await fetch(`${BASE_URL}/chat/${reportId}/history`, {
        method: 'GET',
        headers: getHeaders(),
      });
      return handleResponse(response);
    },
  },
};
