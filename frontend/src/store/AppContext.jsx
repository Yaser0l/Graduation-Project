import React, { createContext, useState, useEffect, useCallback } from 'react';
import { mockData } from '../mockData';
import { api } from '../services/api';

export const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [language, setLanguage] = useState('en');
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [activeVehicle, setActiveVehicle] = useState(null);
  const [diagnostics, setDiagnostics] = useState([]);
  const [maintenance, setMaintenance] = useState(mockData.maintenanceTimeline);
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState(null);

  // Persistence and initial state
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) setUser(JSON.parse(savedUser));
  }, []);

  // Fetch initial data when token is available
  const fetchAppData = useCallback(async () => {
    if (!token) return;
    try {
      const vList = await api.vehicles.list();
      if (vList.length > 0) setActiveVehicle(vList[0]);
      
      const dList = await api.diagnostics.list();
      setDiagnostics(dList);
    } catch (err) {
      console.error("Failed to fetch app data:", err);
      // If token is invalid, logout
      if (err.message.includes('401') || err.message.includes('Unauthorized')) {
        logout();
      }
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      fetchAppData();
    }
  }, [token, fetchAppData]);

  // SSE for Real-time updates
  useEffect(() => {
    if (!token) return;

    let eventSource;
    try {
      // Connect to SSE endpoint with token
      eventSource = new EventSource(`http://localhost:5000/api/events?token=${token}`);
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("SSE Event Received:", data);
        
        if (data.type === 'report_created') {
          // Add new report to list or refresh
          setDiagnostics(prev => [data.report, ...prev]);
          setIsScanning(false);
        }
      };

      eventSource.onerror = (err) => {
        console.error("SSE Connection Error:", err);
        eventSource.close();
      };
    } catch (err) {
      console.error("Failed to setup SSE:", err);
    }

    return () => {
      if (eventSource) eventSource.close();
    };
  }, [token]);

  useEffect(() => {
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = language;
  }, [language]);

  const login = async (email, password) => {
    setError(null);
    try {
      const data = await api.auth.login(email, password);
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const register = async (name, email, password) => {
    setError(null);
    try {
      const data = await api.auth.register(name, email, password);
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    setActiveVehicle(null);
    setDiagnostics([]);
  };

  const toggleLanguage = () => {
    setLanguage(prev => prev === 'en' ? 'ar' : 'en');
  };

  const startScan = () => {
    setIsScanning(true);
    // Real scanning is triggered by MQTT in the backend
    // This state is just for UI loading indicators
  };

  return (
    <AppContext.Provider value={{
      language, toggleLanguage,
      user, token, login, register, logout, error,
      activeVehicle, setActiveVehicle,
      diagnostics, setDiagnostics, fetchAppData,
      maintenance, setMaintenance,
      isScanning, setIsScanning, startScan
    }}>
      {children}
    </AppContext.Provider>
  );
};
