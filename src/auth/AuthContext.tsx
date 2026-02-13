import { createContext, useContext, useMemo, useState } from 'react'

export type Role = 'OFFICER' | 'SUPERVISOR'

export type AuthUser = {
  userId: string
  email: string
  role: Role
}

type AuthState = {
  token: string | null
  user: AuthUser | null
}

type AuthContextValue = AuthState & {
  login: (args: { token: string; user: AuthUser }) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('fd_token'))
  const [user, setUser] = useState<AuthUser | null>(() => {
    const raw = localStorage.getItem('fd_user')
    return raw ? (JSON.parse(raw) as AuthUser) : null
  })

  const value = useMemo<AuthContextValue>(() => {
    return {
      token,
      user,
      login: ({ token: nextToken, user: nextUser }) => {
        localStorage.setItem('fd_token', nextToken)
        localStorage.setItem('fd_user', JSON.stringify(nextUser))
        setToken(nextToken)
        setUser(nextUser)
      },
      logout: () => {
        localStorage.removeItem('fd_token')
        localStorage.removeItem('fd_user')
        setToken(null)
        setUser(null)
      },
    }
  }, [token, user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
