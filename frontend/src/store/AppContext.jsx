import React, { createContext, useState, useEffect } from 'react';
import { mockData } from '../mockData';

export const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [language, setLanguage] = useState('en'); 
  const [activeVehicle, setActiveVehicle] = useState(mockData.vehicles[0]);
  const [diagnostics] = useState(mockData.diagnostics);
  const [maintenance] = useState(mockData.maintenanceTimeline);
  const [isScanning, setIsScanning] = useState(false);

  useEffect(() => {
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = language;
  }, [language]);

  const toggleLanguage = () => {
    setLanguage(prev => prev === 'en' ? 'ar' : 'en');
  };

  return (
    <AppContext.Provider value={{
      language, toggleLanguage,
      activeVehicle, setActiveVehicle,
      diagnostics, maintenance, mockData,
      isScanning, setIsScanning
    }}>
      {children}
    </AppContext.Provider>
  );
};
