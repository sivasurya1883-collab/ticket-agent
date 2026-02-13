import { Navigate, Route, Routes } from 'react-router-dom'

import Layout from '../components/Layout'
import { useAuth } from '../auth/AuthContext'
import DashboardPage from '../pages/DashboardPage'
import CustomerAIAnalysisPage from '../pages/CustomerAIAnalysisPage'
import CreateFDPage from '../pages/CreateFDPage'
import FDRegisterPage from '../pages/FDRegisterPage'
import LoginPage from '../pages/LoginPage'
import SettingsPage from '../pages/SettingsPage'
import ProtectedRoute from './ProtectedRoute'

export default function AppRoutes() {
  const { token, user } = useAuth()

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/customer-ai" element={<CustomerAIAnalysisPage />} />
          <Route path="/fds" element={<FDRegisterPage />} />
          <Route path="/fds/new" element={<CreateFDPage />} />
          <Route element={<ProtectedRoute roles={['SUPERVISOR']} />}>
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to={token && user ? '/' : '/login'} replace />} />
    </Routes>
  )
}
