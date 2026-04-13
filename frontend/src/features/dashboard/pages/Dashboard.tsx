import { useAuth } from '../../auth/hooks/useAuth'
import { Navigate } from 'react-router-dom'

const Dashboard = () => {
  const { user } = useAuth()

  if (!user) {
    return <Navigate to="/" replace />
  }

  const rolePath = user.role === 'student' ? '/student' : user.role === 'instructor' ? '/instructor' : user.role === 'admin' ? '/head' : '/login'
  return <Navigate to={rolePath} replace />
}

export default Dashboard
