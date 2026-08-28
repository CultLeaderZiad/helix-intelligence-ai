import { useState } from "react"
import { Button } from "@/components/ui/Button"
import { Tag } from "@/components/ui/Tag"
import { adminService } from "@/services"

export function UsersTable({ users, onRefresh }) {
  const [updatingId, setUpdatingId] = useState(null)
  
  const handleToggleStatus = async (user) => {
    const isSuspended = user.status === "suspended"
    const newStatus = isSuspended ? "active" : "suspended"
    
    if (!window.confirm(`Are you sure you want to ${isSuspended ? 'reactivate' : 'suspend'} this user?`)) {
      return
    }
    
    setUpdatingId(user.id)
    try {
      await adminService.updateUserStatus(user.id, newStatus)
      if (onRefresh) onRefresh()
    } catch (err) {
      alert("Failed to update status: " + err.message)
    } finally {
      setUpdatingId(null)
    }
  }

  if (!users || users.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-neutral-500">
        No users found.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm text-neutral-400">
        <thead className="border-b border-neutral-800 bg-neutral-900/50 text-neutral-500">
          <tr>
            <th className="px-4 py-3 font-medium">User Email</th>
            <th className="px-4 py-3 font-medium">Role</th>
            <th className="px-4 py-3 font-medium">Organization</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-800/50">
          {users.map((user) => {
            const isSuspended = user.status === "suspended"
            
            return (
              <tr key={user.id} className="transition-colors hover:bg-neutral-800/20">
                <td className="px-4 py-3">
                  <div className="font-medium text-neutral-200">{user.email}</div>
                  <div className="text-xs text-neutral-500 font-mono mt-0.5">{user.id.split('-')[0]}...</div>
                </td>
                <td className="px-4 py-3">
                  <Tag tone={user.role === "admin" ? "brand" : "default"}>{user.role}</Tag>
                </td>
                <td className="px-4 py-3 text-neutral-300">
                  {user.organization_name || "None"}
                </td>
                <td className="px-4 py-3">
                  <Tag tone={isSuspended ? "danger" : "success"}>
                    {isSuspended ? "Suspended" : "Active"}
                  </Tag>
                </td>
                <td className="px-4 py-3 text-right">
                  <Button 
                    size="xs" 
                    variant={isSuspended ? "primary" : "secondary"}
                    disabled={updatingId === user.id}
                    onClick={() => handleToggleStatus(user)}
                  >
                    {updatingId === user.id ? "..." : (isSuspended ? "Reactivate" : "Suspend")}
                  </Button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
