import { useState } from "react"
import { Button } from "@/components/ui/Button"
import { Tag } from "@/components/ui/Tag"
import { adminService } from "@/services"
import { useLanguage } from "@/context/LanguageContext"
import { adminAccessLabel, adminAccountStatusLabel, adminMessage, adminRoleLabel, getAdminAccessStatus } from "@/i18n/adminMessages"

export function UsersTable({ users, onRefresh }) {
  const { lang } = useLanguage()
  const [updatingId, setUpdatingId] = useState(null)
  
  const handleToggleStatus = async (user) => {
    const isSuspended = user.status === "suspended"
    const newStatus = isSuspended ? "active" : "suspended"
    
    if (!window.confirm(adminMessage(lang, "Are you sure you want to {action} this user?", {
      action: adminMessage(lang, isSuspended ? "reactivate" : "suspend"),
    }))) {
      return
    }
    
    setUpdatingId(user.id)
    try {
      await adminService.updateUserStatus(user.id, newStatus)
      if (onRefresh) onRefresh()
    } catch (err) {
      console.error("Failed to update user status", err)
      alert(adminMessage(lang, "Failed to update status."))
    } finally {
      setUpdatingId(null)
    }
  }

  if (!users || users.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-neutral-500">
        {adminMessage(lang, "No users found.")}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-start text-sm text-neutral-400">
        <thead className="border-b border-neutral-800 bg-neutral-900/50 text-neutral-500">
          <tr>
            <th className="px-4 py-3 font-medium">{adminMessage(lang, "User Email")}</th>
            <th className="px-4 py-3 font-medium">{adminMessage(lang, "Role")}</th>
            <th className="px-4 py-3 font-medium">{adminMessage(lang, "Organization / Access")}</th>
            <th className="px-4 py-3 font-medium">{adminMessage(lang, "Account status")}</th>
            <th className="px-4 py-3 font-medium text-end">{adminMessage(lang, "Actions")}</th>
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
                  <Tag className="" tone={user.role === "admin" ? "brand" : "default"}>{adminRoleLabel(lang, user.role)}</Tag>
                </td>
                <td className="px-4 py-3 text-neutral-300">
                  <div>{user.organization_name || adminMessage(lang, "None")}</div>
                  <div className="text-xs text-emerald-300">{adminAccessLabel(lang, getAdminAccessStatus(user), Boolean(user.organization_id))}</div>
                </td>
                <td className="px-4 py-3">
                  <Tag className="" tone={isSuspended ? "danger" : "success"}>
                    {adminAccountStatusLabel(lang, user.status)}
                  </Tag>
                </td>
                <td className="px-4 py-3 text-right">
                  <Button 
                    size="xs" 
                    variant={isSuspended ? "primary" : "default"}
                    disabled={updatingId === user.id}
                    onClick={() => handleToggleStatus(user)}
                  >
                    {updatingId === user.id ? "..." : adminMessage(lang, isSuspended ? "Reactivate" : "Suspend")}
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
