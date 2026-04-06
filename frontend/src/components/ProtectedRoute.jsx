import React, { useContext } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { AppContext } from '../store/AppContext';

export default function ProtectedRoute() {
  const { token } = useContext(AppContext);

  if (!token) {
    return <Navigate to="/welcome" replace />;
  }

  return <Outlet />;
}
