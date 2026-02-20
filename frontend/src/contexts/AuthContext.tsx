'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { authApi } from '@/lib/api-client'

interface User {
  id: string
  name: string
  email: string
  roles: string[]
}

interface AuthContextType {
  user: User | null
  token: string | null
  loading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const STORAGE_KEYS = {
  TOKEN: 'industry-aiflow-token',
  USER: 'industry-aiflow-user'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  // When initialized fromlocalStoragerestore state
  useEffect(() => {
    const initAuth = () => {
      try {
        const storedToken = localStorage.getItem(STORAGE_KEYS.TOKEN)
        const storedUser = localStorage.getItem(STORAGE_KEYS.USER)
        
        if (storedToken && storedUser) {
          setToken(storedToken)
          setUser(JSON.parse(storedUser))
        }
      } catch (err) {
        console.error('Failed to restore auth state:', err)
        clearAuthState()
      } finally {
        setLoading(false)
      }
    }

    initAuth()
  }, [])

  const clearAuthState = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem(STORAGE_KEYS.TOKEN)
    localStorage.removeItem(STORAGE_KEYS.USER)
  }

  const saveAuthState = (newToken: string, newUser: User) => {
    setToken(newToken)
    setUser(newUser)
    localStorage.setItem(STORAGE_KEYS.TOKEN, newToken)
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(newUser))
  }

  const login = async (email: string, password: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await authApi.login(email, password)
      saveAuthState(response.token, response.user)
      router.push('/overview')
    } catch (err: any) {
      const errorMessage = err?.message || 'Login failed, please check your email and password'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const register = async (name: string, email: string, password: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await authApi.register(name, email, password)
      saveAuthState(response.token, response.user)
      router.push('/overview')
    } catch (err: any) {
      const errorMessage = err?.message || 'Registration failed, please try again later'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const logout = async () => {
    setLoading(true)
    
    try {
      await authApi.logout()
    } catch (err) {
      console.error('Logout API error:', err)
      // even thoughAPIIf it fails, the local status must also be cleared.
    } finally {
      clearAuthState()
      setLoading(false)
      router.push('/login')
    }
  }

  const clearError = () => {
    setError(null)
  }

  const value = {
    user,
    token,
    loading,
    error,
    login,
    register,
    logout,
    clearError
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}