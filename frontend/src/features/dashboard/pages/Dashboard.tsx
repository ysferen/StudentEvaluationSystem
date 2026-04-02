import { useAuth } from '../../auth/hooks/useAuth'
import { Navigate } from 'react-router-dom'
import GuestDashboard from './GuestDashboard'

const Dashboard = () => {
  const { user } = useAuth()

  if (!user) {
    return <GuestDashboard />
  }

  const getRoleBasedDashboard = () => {
    switch (user.role) {
      case 'student':
        return <Navigate to="/student" replace />
      case 'instructor':
        return <Navigate to="/lecturer" replace />
      case 'admin':
        return <Navigate to="/lecturer" replace /> // Admin can use lecturer dashboard for now
      default:
        return <Navigate to="/login" replace />
    }
  }

  return (
    <div>
      {getRoleBasedDashboard()}
    </div>
  )
}

export default Dashboard
