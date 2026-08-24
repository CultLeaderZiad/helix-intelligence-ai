import { useState } from "react"
import { Button } from "@/components/ui/Button"
import { Tag } from "@/components/ui/Tag"
import { adminService } from "@/services"

export function OrganizationsTable({ organizations, onRefresh }) {
  const [grantingId, setGrantingId] = useState(null)
  
  const handleGrantCredits = async (orgId) => {
    const amountStr = window.prompt("Enter amount of trial credits to grant:")
    if (!amountStr) return
    const amount = parseFloat(amountStr)
    if (isNaN(amount) || amount <= 0) {
      alert("Invalid amount.")
      return
    }
    
    setGrantingId(orgId)
    try {
      await adminService.grantCredits(orgId, amount)
      if (onRefresh) onRefresh()
    } catch (err) {
      alert("Failed to grant credits: " + err.message)
    } finally {
      setGrantingId(null)
    }
  }

  if (!organizations || organizations.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-neutral-500">
        No organizations found.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm text-neutral-400">
        <thead className="border-b border-neutral-800 bg-neutral-900/50 text-neutral-500">
          <tr>
            <th className="px-4 py-3 font-medium">Organization</th>
            <th className="px-4 py-3 font-medium">Owner</th>
            <th className="px-4 py-3 font-medium">Plan</th>
            <th className="px-4 py-3 font-medium">Trial Expiry</th>
            <th className="px-4 py-3 font-medium text-right">Credits Used/Rem</th>
            <th className="px-4 py-3 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-800/50">
          {organizations.map((org) => {
            const isTrial = org.plan_id === "plan_trial_default"
            
            return (
              <tr key={org.id} className="transition-colors hover:bg-neutral-800/20">
                <td className="px-4 py-3">
                  <div className="font-medium text-neutral-200">{org.name}</div>
                  <div className="text-xs text-neutral-500 font-mono mt-0.5">{org.id.split('_')[1]}</div>
                </td>
                <td className="px-4 py-3">{org.owner_email}</td>
                <td className="px-4 py-3">
                  <Tag tone={isTrial ? "warning" : "default"}>{org.plan_type}</Tag>
                </td>
                <td className="px-4 py-3">
                  {org.trial_expires_at ? new Date(org.trial_expires_at).toLocaleDateString() : "N/A"}
                </td>
                <td className="px-4 py-3 text-right font-mono">
                  {org.credits_used.toFixed(1)} / {org.credit_balance.toFixed(1)}
                </td>
                <td className="px-4 py-3 text-right">
                  <Button 
                    size="xs" 
                    variant="secondary"
                    disabled={grantingId === org.id}
                    onClick={() => handleGrantCredits(org.id)}
                  >
                    {grantingId === org.id ? "..." : "+ Credits"}
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
