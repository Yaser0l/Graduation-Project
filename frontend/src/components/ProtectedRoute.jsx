import React, { useContext } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { AuthContext } from '../store/AppContext';

export default function ProtectedRoute() {
  const { token } = useContext(AuthContext);

  if (!token) {
    return <Navigate to="/welcome" replace />;
  }

  return <Outlet />;
}
