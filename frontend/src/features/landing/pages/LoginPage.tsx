import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../../auth/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import LoginIllustration from '../components/LoginIllustration'

const LoginPage = () => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const { login, isAuthenticated, user } = useAuth()

  if (isAuthenticated && user) {
    const rolePath = user.role === 'instructor' ? '/instructor' : user.role === 'admin' ? '/head' : user.role === 'student' ? '/student' : '/login'
    return <Navigate to={rolePath} replace />
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      await login(username, password)
    } catch (err: unknown) {
      let message = 'Login failed. Please try again.'
      try {
        const errObj = err as Record<string, unknown>
        const response = errObj?.response as Record<string, unknown> | undefined
        const data = response?.data as Record<string, unknown> | undefined
        if (data) {
          const raw = data?.error ?? data?.message ?? data?.detail
          if (typeof raw === 'string') {
            message = raw
          } else if (typeof raw === 'object' && raw !== null) {
            const rawObj = raw as Record<string, unknown>
            message = (typeof rawObj?.message === 'string' ? rawObj.message : null) ?? (typeof rawObj?.code === 'string' ? rawObj.code : null) ?? message
          }
        }
      } catch {
        // ignore extraction errors
      }
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      <LoginIllustration />

      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 sm:p-12">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-bold text-secondary-900 mb-1">Welcome back</h1>
          <p className="text-secondary-500 mb-8">Sign in to your account</p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isLoading}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                required
              />
            </div>

            {error && (
              <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>

          <div className="mt-6 pt-4 border-t text-sm text-secondary-500">
            <p className="font-medium mb-2">Demo Accounts:</p>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <span className="font-semibold">Admin:</span>
                <br />
                admin / admin
              </div>
              <div>
                <span className="font-semibold">Lecturer:</span>
                <br />
                lecturer / lecturer
              </div>
              <div>
                <span className="font-semibold">Student:</span>
                <br />
                student / student
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
