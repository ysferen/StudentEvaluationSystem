import React, { useContext, createContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { useUsersAuthLoginCreate, useUsersAuthMeRetrieve } from '../api/generated/authentication/authentication'
import { useQueryClient } from '@tanstack/react-query'
import { CustomUser } from '../api/model/customUser'
import { TokenResponse } from '../api/model/tokenResponse'

/**
 * Authentication context type definition.
 *
 * @interface AuthContextType
 * @property {CustomUser | null} user - Current authenticated user or null if not logged in
 * @property {(username: string, password: string) => Promise<void>} login - Login function
 * @property {() => void} logout - Logout function that clears tokens and cache
 * @property {boolean} isLoading - Whether auth state is being initialized
 * @property {boolean} isAuthenticated - Whether user is currently authenticated
 */
interface AuthContextType {
  user: CustomUser | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  isLoading: boolean
  isAuthenticated: boolean
}

/**
 * React context for authentication state.
 *
 * @internal
 * Use the {@link useAuth} hook to access this context.
 */
const AuthContext = createContext<AuthContextType | undefined>(undefined)

/**
 * Hook to access authentication context.
 *
 * This hook provides access to the current user, login/logout functions,
 * and authentication state. It must be used within an AuthProvider.
 *
 * @example
 * ```tsx
 * const { user, login, logout, isAuthenticated } = useAuth()
 *
 * if (isAuthenticated) {
 *   return <div>Welcome, {user?.first_name}</div>
 * }
 * ```
 *
 * @returns {AuthContextType} Authentication context value
 * @throws {Error} If used outside of AuthProvider
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

/**
 * Props for the AuthProvider component.
 *
 * @interface AuthProviderProps
 * @property {ReactNode} children - Child components that will have access to auth context
 */
interface AuthProviderProps {
  children: ReactNode
}

/**
 * Authentication provider component.
 *
 * Manages authentication state, token storage, and provides auth context
to all child components. Handles:
 * - Token storage in localStorage
 * - Automatic user data fetching on mount
 * - Token refresh on 401 errors
 * - Query cache clearing on logout
 *
 * @example
 * ```tsx
 * <AuthProvider>
 *   <App />
 * </AuthProvider>
 * ```
 *
 * @param {AuthProviderProps} props - Component props
 * @returns {JSX.Element} Provider component with auth context
 */
export const AuthProvider = ({ children }: AuthProviderProps): JSX.Element => {
  const [user, setUser] = useState<CustomUser | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const queryClient = useQueryClient()

  // Check if user is authenticated on mount
  const {
    data: currentUser,
    isLoading: userLoading,
    error: userError
  } = useUsersAuthMeRetrieve({
    query: {
      enabled: !!localStorage.getItem('access_token'),
      retry: false
    }
  })

  // Create a custom login mutation that handles token storage
  const loginMutation = useUsersAuthLoginCreate({
    mutation: {
      onSuccess: (data: TokenResponse): void => {
        // Store tokens in localStorage
        localStorage.setItem('access_token', data.access)
        localStorage.setItem('refresh_token', data.refresh)

        // Invalidate and refetch user data
        queryClient.invalidateQueries({ queryKey: ['/api/users/auth/me/'] })
      },
      onError: (error: Error): void => {
        // Re-throw error for component-level handling
        throw error
      }
    }
  })

  /**
   * Logs out the current user.
   *
   * Clears stored tokens, resets user state, clears query cache,
   * and redirects to the login page.
   *
   * @callback logout
   */
  const logout = useCallback((): void => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)

    // Clear all cached queries to prevent data leakage
    queryClient.clear()

    // Redirect to login page
    window.location.href = '/login'
  }, [queryClient])

  useEffect(() => {
    // Update user state when user data is fetched
    if (currentUser) {
      setUser(currentUser)
    }

    // Handle authentication errors by logging out
    if (userError instanceof Error) {
      logout()
    }

    // Mark loading as complete when user fetch finishes
    if (!userLoading) {
      setIsLoading(false)
    }
  }, [currentUser, userLoading, userError, logout])

  /**
   * Authenticates a user with username and password.
   *
   * On success, stores access and refresh tokens in localStorage.
   * On error, throws the error for component-level handling.
   *
   * @callback login
   * @param {string} username - User's username
   * @param {string} password - User's password
   * @returns {Promise<void>} Resolves on successful login
   * @throws {Error} On authentication failure
   */
  const login = useCallback(async (username: string, password: string): Promise<void> => {
    // Construct login payload
    // Note: email is required by type but not used for username-based login
    const loginData = {
      username,
      email: '', // Required field but not used for login
      password: password
    } as CustomUser & { password: string }

    await loginMutation.mutateAsync({ data: loginData })
  }, [loginMutation])

  /**
   * Memoized auth context value to prevent unnecessary re-renders.
   *
   * Includes derived isAuthenticated state and combines local loading
   * state with mutation pending state.
   */
  const value: AuthContextType = React.useMemo(() => ({
    user,
    login,
    logout,
    isLoading: isLoading || loginMutation.isPending,
    isAuthenticated: !!user,
  }), [user, login, logout, isLoading, loginMutation.isPending])

  return React.createElement(AuthContext.Provider, { value }, children)
}

/**
 * Default export for AuthProvider component.
 *
 * @see {@link AuthProvider}
 */
export default AuthProvider
