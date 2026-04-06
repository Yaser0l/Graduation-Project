import React, { createContext, useState, useEffect, useCallback } from 'react';
import { api, EVENTS_BASE_URL } from '../services/api';

export const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [language, setLanguage] = useState('en');
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  // All user vehicles (real data from GET /api/vehicles/)
  const [vehicles, setVehicles] = useState([]);
  const [activeVehicle, setActiveVehicleState] = useState(null);

  // Real diagnostic reports — filtered by active vehicle
  const [diagnostics, setDiagnostics] = useState([]);
  const [maintenance, setMaintenance] = useState([]);
  const [oilChangeProgramKm, setOilChangeProgramKm] = useState(() => {
    const saved = localStorage.getItem('oilChangeProgramKm');
    return saved === '5000' ? '5000' : '10000';
  });

  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState(null);
  const [isLoadingData, setIsLoadingData] = useState(false);

  const fetchMaintenanceForVehicle = useCallback(async (vehicle) => {
    if (!token || !vehicle) {
      setMaintenance([]);
      return;
    }
    try {
      const programKm = oilChangeProgramKm === '5000' ? 5000 : 10000;
      const list = await api.maintenance.listByVehicle(vehicle.id, programKm);
      setMaintenance(list);
    } catch (err) {
      console.error('Failed to fetch maintenance for vehicle:', err);
      setMaintenance([]);
    }
  }, [token, oilChangeProgramKm]);

  useEffect(() => {
    fetchMaintenanceForVehicle(activeVehicle);
  }, [activeVehicle, fetchMaintenanceForVehicle]);

  const setOilChangeProgram = useCallback((programKm) => {
    const next = programKm === '5000' ? '5000' : '10000';
    setOilChangeProgramKm(next);
    localStorage.setItem('oilChangeProgramKm', next);
  }, []);

  const completeMaintenanceTask = useCallback((taskId) => {
    if (!activeVehicle || !taskId) return Promise.resolve();
    return api.maintenance.completeTask(activeVehicle.id, taskId)
      .then(() => fetchMaintenanceForVehicle(activeVehicle))
      .catch((err) => {
        console.error('Failed to complete maintenance task:', err);
        throw err;
      });
  }, [activeVehicle, fetchMaintenanceForVehicle]);

  // ─── Persist active vehicle to localStorage ────────────────────────────────
  // Wrap setActiveVehicle so we always sync to localStorage
  const setActiveVehicle = useCallback((vehicle) => {
    setActiveVehicleState(vehicle);
    if (vehicle) {
      localStorage.setItem('activeVehicleId', vehicle.id);
    } else {
      localStorage.removeItem('activeVehicleId');
    }
  }, []);

  // Rehydrate user from localStorage on mount
  useEffect(() => {
    try {
      const savedUser = localStorage.getItem('user');
      if (savedUser) setUser(JSON.parse(savedUser));
    } catch (e) {
      console.error('Failed to parse user from localStorage', e);
      localStorage.removeItem('user');
      setUser(null);
    }
  }, []);

  // ─── Fetch diagnostics whenever active vehicle changes ────────────────────
  const fetchDiagnosticsForVehicle = useCallback(async (vehicle) => {
    if (!token || !vehicle) {
      setDiagnostics([]);
      return;
    }
    try {
      const dList = await api.diagnostics.listByVehicle(vehicle.id);
      setDiagnostics(dList);
    } catch (err) {
      console.error('Failed to fetch diagnostics for vehicle:', err);
      setDiagnostics([]);
    }
  }, [token]);

  // Re-fetch diagnostics whenever active vehicle changes
  useEffect(() => {
    fetchDiagnosticsForVehicle(activeVehicle);
  }, [activeVehicle, fetchDiagnosticsForVehicle]);

  // ─── Fetch vehicles from backend ──────────────────────────────────────────
  const fetchAppData = useCallback(async () => {
    if (!token) return;
    setIsLoadingData(true);
    try {
      const vList = await api.vehicles.list();
      setVehicles(vList);

      // Restore previously selected vehicle from localStorage, fallback to first
      const savedId = localStorage.getItem('activeVehicleId');
      setActiveVehicleState(prev => {
        if (prev) {
          // Keep current selection if it still exists in the new list
          const refreshed = vList.find(v => v.id === prev.id);
          if (refreshed) return refreshed;
        }
        if (savedId) {
          const saved = vList.find(v => v.id === savedId);
          if (saved) return saved;
        }
        return vList[0] || null;
      });

    } catch (err) {
      console.error('Failed to fetch app data:', err);
      if (err.message.includes('401') || err.message.includes('Unauthorized')) {
        logout();
      }
    } finally {
      setIsLoadingData(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (token) fetchAppData();
  }, [token, fetchAppData]);

  // ─── SSE — real-time diagnostic results ──────────────────────────────────
  useEffect(() => {
    if (!token) return;
    let es;
    let reconnectTimer;

    const parseIncomingPayload = (raw) => {
      try {
        return typeof raw === 'string' ? JSON.parse(raw) : raw;
      } catch {
        return null;
      }
    };

    const handleIncomingEvent = (payload) => {
      if (!payload) return;
      const report = payload.report || payload.data || payload;
      const eventType = payload.type || payload.event;
      const isReportCreated = eventType === 'report_created' || eventType === 'diagnostic:new' || Boolean(report?.vehicle_id);

      if (!isReportCreated || !report) return;

      // Only add to the list if it belongs to the current active vehicle
      setActiveVehicleState(currentVehicle => {
        if (currentVehicle && report.vehicle_id === currentVehicle.id) {
          setDiagnostics(prev => [report, ...prev]);
        }
        setIsScanning(false);
        return currentVehicle;
      });
    };

    const connectSSE = () => {
      try {
        es = new EventSource(`${EVENTS_BASE_URL}/api/events?token=${token}`);
        es.onmessage = (event) => handleIncomingEvent(parseIncomingPayload(event.data));
        es.addEventListener('diagnostic:new', (event) => handleIncomingEvent(parseIncomingPayload(event.data)));
        es.onerror = () => {
          console.error('SSE Error. Reconnecting in 5s...');
          es.close();
          reconnectTimer = setTimeout(connectSSE, 5000);
        };
      } catch (e) {
        console.error('SSE setup failed:', e);
        reconnectTimer = setTimeout(connectSSE, 5000);
      }
    };

    connectSSE();

    return () => { 
      if (es) es.close(); 
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [token]);

  // ─── RTL / language ────────────────────────────────────────────────────────
  useEffect(() => {
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = language;
  }, [language]);

  // ─── Auth ──────────────────────────────────────────────────────────────────
  const login = async (email, password) => {
    setError(null);
    const data = await api.auth.login(email, password).catch(err => {
      setError(err.message);
      throw err;
    });
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
    return data;
  };

  const register = async (name, email, password) => {
    setError(null);
    const data = await api.auth.register(name, email, password).catch(err => {
      setError(err.message);
      throw err;
    });
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
    return data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('activeVehicleId');
    setToken(null);
    setUser(null);
    setVehicles([]);
    setActiveVehicleState(null);
    setDiagnostics([]);
    setMaintenance([]);
  };

  // ─── Vehicle helpers ────────────────────────────────────────────────────────
  /** Create a new vehicle via POST /api/vehicles/ and make it active */
  const addVehicle = async (vehicleData) => {
    const newVehicle = await api.vehicles.create(vehicleData);
    setVehicles(prev => [...prev, newVehicle]);
    setActiveVehicle(newVehicle); // also persists to localStorage
    return newVehicle;
  };

  /** Update vehicle mileage and refresh local state for the active vehicle. */
  const updateVehicleMileage = async (vehicleId, mileage) => {
    const updated = await api.vehicles.update(vehicleId, { mileage });

    setVehicles(prev => prev.map(v => (v.id === vehicleId ? { ...v, ...updated } : v)));
    setActiveVehicleState(prev => (prev && prev.id === vehicleId ? { ...prev, ...updated } : prev));

    return updated;
  };

  /** Resolve a diagnostic report and mark it removed from active problem lists. */
  const resolveDiagnostic = async (reportId) => {
    const resolved = await api.diagnostics.resolve(reportId);
    setDiagnostics(prev => prev.map(report => (
      report.id === reportId
        ? { ...report, ...resolved, resolved: true }
        : report
    )));
    return resolved;
  };

  // ─── Misc ────────────────────────────────────────────────────────────────────
  const toggleLanguage = () => setLanguage(prev => (prev === 'en' ? 'ar' : 'en'));
  const startScan = () => setIsScanning(true);

  return (
    <AppContext.Provider value={{
      // auth
      user, token, login, register, logout, error,
      // language
      language, toggleLanguage,
      // vehicles (real)
      vehicles, setVehicles, activeVehicle, setActiveVehicle, addVehicle, updateVehicleMileage,
      // diagnostics (real, per-vehicle)
      diagnostics, setDiagnostics,
      resolveDiagnostic,
      // maintenance (regular periodic schedule)
      maintenance,
      completeMaintenanceTask,
      oilChangeProgramKm,
      setOilChangeProgram,
      // data refresh
      fetchAppData, isLoadingData,
      // scanning
      isScanning, setIsScanning, startScan,
    }}>
      {children}
    </AppContext.Provider>
  );
};
