import React, { createContext, useState, useEffect, useCallback, useContext } from 'react';
import { api, EVENTS_BASE_URL } from '../services/api';

export const AuthContext = createContext();
export const VehicleContext = createContext();
export const DiagnosticContext = createContext();
export const LanguageContext = createContext();

export const AppProvider = ({ children }) => {
  // --- Language State ---
  const [language, setLanguage] = useState('en');

  useEffect(() => {
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = language;
  }, [language]);

  const toggleLanguage = () => setLanguage((prev) => (prev === 'en' ? 'ar' : 'en'));

  // --- Auth State ---
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [authError, setAuthError] = useState(null);

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

  const login = async (email, password) => {
    setAuthError(null);
    const data = await api.auth.login(email, password).catch((err) => {
      setAuthError(err.message);
      throw err;
    });
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
    return data;
  };

  const register = async (name, email, password) => {
    setAuthError(null);
    const data = await api.auth.register(name, email, password).catch((err) => {
      setAuthError(err.message);
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
  };

  // --- Vehicle State ---
  const [vehicles, setVehicles] = useState([]);
  const [activeVehicle, setActiveVehicleState] = useState(null);
  const [isLoadingData, setIsLoadingData] = useState(false);

  const setActiveVehicle = useCallback((vehicle) => {
    setActiveVehicleState(vehicle);
    if (vehicle) {
      localStorage.setItem('activeVehicleId', vehicle.id);
    } else {
      localStorage.removeItem('activeVehicleId');
    }
  }, []);

  const fetchAppData = useCallback(async () => {
    if (!token) {
      setVehicles([]);
      setActiveVehicleState(null);
      return;
    }
    setIsLoadingData(true);
    try {
      const vList = await api.vehicles.list();
      setVehicles(vList);

      const savedId = localStorage.getItem('activeVehicleId');
      setActiveVehicleState((prev) => {
        if (prev) {
          const refreshed = vList.find((v) => v.id === prev.id);
          if (refreshed) return refreshed;
        }
        if (savedId) {
          const saved = vList.find((v) => v.id === savedId);
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
  }, [token]);

  useEffect(() => {
    if (token) fetchAppData();
    else {
      setVehicles([]);
      setActiveVehicleState(null);
    }
  }, [token, fetchAppData]);

  const addVehicle = async (vehicleData) => {
    const newVehicle = await api.vehicles.create(vehicleData);
    setVehicles((prev) => [...prev, newVehicle]);
    setActiveVehicle(newVehicle);
    return newVehicle;
  };

  const updateVehicleMileage = async (vehicleId, mileage) => {
    const updated = await api.vehicles.update(vehicleId, { mileage });
    setVehicles((prev) =>
      prev.map((v) => (v.id === vehicleId ? { ...v, ...updated } : v))
    );
    setActiveVehicleState((prev) =>
      prev && prev.id === vehicleId ? { ...prev, ...updated } : prev
    );
    return updated;
  };

  // --- Diagnostic State ---
  const [diagnostics, setDiagnostics] = useState([]);
  const [maintenance, setMaintenance] = useState([]);
  const [maintenanceError, setMaintenanceError] = useState(null);
  const [isMaintenanceLoading, setIsMaintenanceLoading] = useState(false);
  const [isScanning, setIsScanning] = useState(false);

  const fetchDiagnosticsForVehicle = useCallback(
    async (vehicle) => {
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
    },
    [token]
  );

  const fetchMaintenanceForVehicle = useCallback(
    async (vehicle) => {
      if (!token || !vehicle) {
        setMaintenance([]);
        setIsMaintenanceLoading(false);
        setMaintenanceError(null);
        return;
      }
      setIsMaintenanceLoading(true);
      try {
        const list = await api.maintenance.listByVehicle(vehicle.id);
        setMaintenance(list);
        setMaintenanceError(null);
      } catch (err) {
        console.error('Failed to fetch maintenance for vehicle:', err);
        setMaintenanceError(err.message || 'Failed to load maintenance data');
      } finally {
        setIsMaintenanceLoading(false);
      }
    },
    [token]
  );

  useEffect(() => {
    fetchDiagnosticsForVehicle(activeVehicle);
    fetchMaintenanceForVehicle(activeVehicle);
    if (!token || !activeVehicle) {
      setDiagnostics([]);
      setMaintenance([]);
    }
  }, [activeVehicle, fetchDiagnosticsForVehicle, fetchMaintenanceForVehicle, token]);

  const completeMaintenanceTask = useCallback(
    Object.assign(async (taskId) => {
      if (!activeVehicle || !taskId) return Promise.resolve();
      return api.maintenance
        .completeTask(activeVehicle.id, taskId)
        .then(() => fetchMaintenanceForVehicle(activeVehicle))
        .catch((err) => {
          console.error('Failed to complete maintenance task:', err);
          throw err;
        });
    }),
    [activeVehicle, fetchMaintenanceForVehicle]
  );

  const resolveDiagnostic = async (reportId) => {
    const resolved = await api.diagnostics.resolve(reportId);
    setDiagnostics((prev) =>
      prev.map((report) =>
        report.id === reportId ? { ...report, ...resolved, resolved: true } : report
      )
    );
    return resolved;
  };

  const startScan = () => setIsScanning(true);

  // SSE logic
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
      const isReportCreated =
        eventType === 'report_created' ||
        eventType === 'diagnostic:new' ||
        Boolean(report?.vehicle_id);

      if (!isReportCreated || !report) return;

      if (activeVehicle && report.vehicle_id === activeVehicle.id) {
        setDiagnostics((prev) => [report, ...prev]);

        const reportMileage = Number(report.mileage_at_fault ?? report.mileage);
        if (Number.isFinite(reportMileage) && reportMileage >= 0) {
          setVehicles((prev) =>
            prev.map((v) =>
              v.id === activeVehicle.id ? { ...v, mileage: Math.max(Number(v.mileage || 0), reportMileage) } : v
            )
          );
          setActiveVehicleState((prev) =>
            prev && prev.id === activeVehicle.id
              ? { ...prev, mileage: Math.max(Number(prev.mileage || 0), reportMileage) }
              : prev
          );
        }

        // Keep maintenance timeline in sync with latest backend mileage/state after new DTC.
        fetchMaintenanceForVehicle(activeVehicle);
      }
      setIsScanning(false);
    };

    const connectSSE = () => {
      try {
        es = new EventSource(`${EVENTS_BASE_URL}/api/events?token=${token}`);
        es.onmessage = (event) => handleIncomingEvent(parseIncomingPayload(event.data));
        es.addEventListener('diagnostic:new', (event) =>
          handleIncomingEvent(parseIncomingPayload(event.data))
        );
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
  }, [token, activeVehicle, fetchMaintenanceForVehicle]);

  // Provide composed contexts
  return (
    <LanguageContext.Provider value={{ language, toggleLanguage }}>
      <AuthContext.Provider value={{ user, token, login, register, logout, error: authError }}>
        <VehicleContext.Provider
          value={{
            vehicles,
            setVehicles,
            activeVehicle,
            setActiveVehicle,
            addVehicle,
            updateVehicleMileage,
            fetchAppData,
            isLoadingData,
          }}
        >
          <DiagnosticContext.Provider
            value={{
              diagnostics,
              setDiagnostics,
              resolveDiagnostic,
              maintenance,
              maintenanceError,
              isMaintenanceLoading,
              completeMaintenanceTask,
              isScanning,
              setIsScanning,
              startScan,
            }}
          >
            {children}
          </DiagnosticContext.Provider>
        </VehicleContext.Provider>
      </AuthContext.Provider>
    </LanguageContext.Provider>
  );
};
