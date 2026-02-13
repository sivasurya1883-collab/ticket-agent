import { Link, NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <header className="app-header">
          <img src="/logo2.png" alt="Twenty1 Bank logo" className="logo" style={{ width: '170px', height: '150px'}}  />
        <Link to="/" className="brand">
          Twenty1 Banking
        </Link>
        <div className="spacer" />
        {user ? (
          <div className="header-right">
            <div className="user-pill">
              <div className="user-email">{user.email}</div>
              <div className="user-role">{user.role}</div>
            </div>
            <button className="btn" onClick={logout}>
              Logout
            </button>
          </div>
        ) : null}
      </header>

      <div className="app-body">
        <aside className="app-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Dashboard
          </NavLink>
          <NavLink to="/fds/new" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Create FD
          </NavLink>
          <NavLink to="/customer-ai" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Customer AI Analysis
          </NavLink>
          <NavLink to="/fds" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            FD Register
          </NavLink>
          {user?.role === 'SUPERVISOR' ? (
            <NavLink to="/settings" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
              Supervisor Settings
            </NavLink>
          ) : null}
        </aside>

        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
