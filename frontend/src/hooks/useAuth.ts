import React, { useContext, createContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { useUsersAuthLoginCreate, useUsersAuthMeRetrieve } from '../api/generated/authentication/authentication'
import { useQueryClient } from '@tanstack/react-query'
import { CustomUser } from '../api/model/customUser'
import { TokenResponse } from '../api/model/tokenResponse'

interface AuthContextType {
  user: CustomUser | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  isLoading: boolean
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [user, setUser] = useState<CustomUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const queryClient = useQueryClient()

  // Check if user is authenticated on mount
  const { data: currentUser, isLoading: userLoading, error: userError } = useUsersAuthMeRetrieve({
    query: {
      enabled: !!localStorage.getItem('access_token'),
      retry: false
    }
  })

  // Create a custom login mutation that accepts password
  const loginMutation = useUsersAuthLoginCreate({
    mutation: {
      onSuccess: (data: TokenResponse) => {
        // Store tokens
        localStorage.setItem('access_token', data.access)
        localStorage.setItem('refresh_token', data.refresh)
        
        // Invalidate and refetch user data
        queryClient.invalidateQueries({ queryKey: ['/api/users/auth/me/'] })
      },
      onError: (error) => {
        // Let the calling component handle the error
        throw error
      }
    }
  })

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
    
    // Clear all cached queries
    queryClient.clear()
    
    // Redirect to login page
    window.location.href = '/login'
  }, [queryClient])

  useEffect(() => {
    if (currentUser) {
      setUser(currentUser)
    }
    if (userError instanceof Error) {
      // Token is invalid, clear it
      logout()
    }
    if (!userLoading) {
      setIsLoading(false)
    }
  }, [currentUser, userLoading, userError, logout])

  const login = useCallback(async (username: string, password: string) => {
    // Create login data - we need to cast to include password since the type doesn't have it
    const loginData = {
      username,
      email: '', // Required field but not used for login
      password: password // This will be sent in the request
    } as CustomUser & { password: string }

    await loginMutation.mutateAsync({ data: loginData })
  }, [loginMutation])

  const value: AuthContextType = React.useMemo(() => ({
    user,
    login,
    logout,
    isLoading: isLoading || loginMutation.isPending,
    isAuthenticated: !!user,
  }), [user, login, logout, isLoading, loginMutation.isPending])

  return React.createElement(AuthContext.Provider, { value }, children)
}

export default AuthProvider
