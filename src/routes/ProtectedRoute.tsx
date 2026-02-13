import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'

export default function ProtectedRoute({ roles }: { roles?: Array<'OFFICER' | 'SUPERVISOR'> }) {
  const { token, user } = useAuth()

  if (!token || !user) {
    return <Navigate to="/login" replace />
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
