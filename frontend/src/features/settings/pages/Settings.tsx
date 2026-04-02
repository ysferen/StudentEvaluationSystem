import React from 'react'
import { useAuth } from '../../auth/hooks/useAuth'

const Settings: React.FC = () => {
  const { isAuthenticated } = useAuth()

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-secondary-900">Settings</h1>
      <p className="mt-4 text-secondary-600">Configure your account and preferences here.</p>

      <section className="mt-8 max-w-md">
        <h2 className="text-lg font-semibold text-secondary-900">Profile</h2>
        <p className="mt-2 text-secondary-600">Update display name and profile preferences from here.</p>
      </section>
    </div>
  )
}

export default Settings
