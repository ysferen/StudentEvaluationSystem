import React, { useContext, createContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { useUsersAuthLoginCreate, useUsersAuthMeRetrieve, usersAuthLogoutCreate, usersAuthMeRetrieve } from '../../../shared/api/generated/authentication/authentication'
import { useQueryClient } from '@tanstack/react-query'
import { CustomUser } from '../../../shared/api/model/customUser'

/**
 * Authentication context type definition.
 *
 * @interface AuthContextType
 * @property {CustomUser | null} user - Current authenticated user or null if not logged in
 * @property {(username: string, password: string) => Promise<void>} login - Login function
 * @property {() => Promise<void>} logout - Logout function that clears tokens and cache
 * @property {boolean} isLoading - Whether auth state is being initialized
 * @property {boolean} isAuthenticated - Whether user is currently authenticated
 */
interface AuthContextType {
  user: CustomUser | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
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
      retry: false,
      // Don't run this query on the login page to avoid unnecessary 401s
      enabled: typeof window !== 'undefined' && window.location.pathname !== '/login'
    }
  })

  // Create a custom login mutation that handles token storage
  const loginMutation = useUsersAuthLoginCreate({
    mutation: {
      onSuccess: async (): Promise<void> => {
        // Tokens are stored in HTTP-only cookies by the server
        // Fetch user data directly since the query may be disabled on /login
        try {
          const userData = await queryClient.fetchQuery({
            queryKey: ['/api/users/auth/me/'],
            queryFn: () => usersAuthMeRetrieve(),
          })
          setUser(userData)
        } catch {
          // If fetch fails, invalidate and let the query handle it
          queryClient.invalidateQueries({ queryKey: ['/api/users/auth/me/'] })
        }
      },
      onError: (): void => {
        // Error is thrown by mutateAsync and handled by the caller
      }
    }
  })

  /**
   * Logs out the current user.
   *
   * Clears stored tokens (cookies), resets user state, clears query cache,
   * and redirects to the login page.
   *
   * @callback logout
   */
  const logout = useCallback(async (): Promise<void> => {
    try {
      // Ask backend to clear HTTP-only cookies and invalidate refresh token.
      await usersAuthLogoutCreate()
    } catch {
      // Even if logout request fails, continue with local state cleanup.
    } finally {
      setUser(null)
      queryClient.clear()
      window.location.href = '/login'
    }
  }, [queryClient])

  useEffect(() => {
    // Update user state when user data is fetched
    if (currentUser) {
      setUser(currentUser)
    }

    // Handle authentication errors by logging out
    // Only logout if user was previously authenticated (user !== null)
    // This prevents redirect loops on public pages like /login
    if (userError instanceof Error && user !== null) {
      void logout()
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
