import React, { useContext } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { AuthContext } from '../store/AppContext';

export default function ProtectedRoute() {
  const { token } = useContext(AuthContext);
  const effectiveToken = token || localStorage.getItem('token');

  if (!effectiveToken) {
    return <Navigate to="/welcome" replace />;
  }

  return <Outlet />;
}
