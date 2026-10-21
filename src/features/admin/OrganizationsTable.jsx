import { useState } from "react"
import { Button } from "@/components/ui/Button"
import { Tag } from "@/components/ui/Tag"
import { adminService } from "@/services"
import { useLanguage } from "@/context/LanguageContext"
import { adminAccessLabel, adminMessage, formatAdminDate, getAdminAccessStatus } from "@/i18n/adminMessages"

export function OrganizationsTable({ organizations, onRefresh }) {
  const { lang } = useLanguage()
  const [grantingId, setGrantingId] = useState(null)
  
  const handleGrantCredits = async (orgId) => {
    const amountStr = window.prompt(adminMessage(lang, "Enter amount of credits to grant:"))
    if (!amountStr) return
    const amount = parseFloat(amountStr)
    if (isNaN(amount) || amount <= 0) {
      alert(adminMessage(lang, "Invalid amount."))
      return
    }
    
    setGrantingId(orgId)
    try {
      await adminService.grantCredits(orgId, amount)
      if (onRefresh) onRefresh()
    } catch (err) {
      console.error("Failed to grant credits", err)
      alert(adminMessage(lang, "Failed to grant credits."))
    } finally {
      setGrantingId(null)
    }
  }

  if (!organizations || organizations.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-neutral-500">
        {adminMessage(lang, "No organizations found.")}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-start text-sm text-neutral-400">
        <thead className="border-b border-neutral-800 bg-neutral-900/50 text-neutral-500">
          <tr>
            <th className="px-4 py-3 font-medium">{adminMessage(lang, "Organization")}</th>
            <th className="px-4 py-3 font-medium">{adminMessage(lang, "Owner")}</th>
            <th className="px-4 py-3 font-medium">{adminMessage(lang, "Access")}</th>
            <th className="px-4 py-3 font-medium text-end">{adminMessage(lang, "Credits Used/Rem")}</th>
            <th className="px-4 py-3 font-medium text-end">{adminMessage(lang, "Actions")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-800/50">
          {organizations.map((org) => {
            return (
              <tr key={org.id} className="transition-colors hover:bg-neutral-800/20">
                <td className="px-4 py-3">
                  <div className="font-medium text-neutral-200">{org.name}</div>
                  <div className="text-xs text-neutral-500 font-mono mt-0.5">{org.id.split('_')[1]}</div>
                </td>
                <td className="px-4 py-3">{org.owner_email}</td>
                <td className="px-4 py-3">
                  <Tag className="" tone={getAdminAccessStatus(org) === "approved" ? "success" : "warning"}>
                    {adminAccessLabel(lang, getAdminAccessStatus(org))}
                  </Tag>
                </td>
                <td className="px-4 py-3 text-end font-mono">
                  {Number(org.credits_used || 0).toFixed(1)} / {Number(org.credit_balance || 0).toFixed(1)}
                </td>
                <td className="px-4 py-3 text-end">
                  <Button 
                    size="xs" 
                    variant="default"
                    disabled={grantingId === org.id}
                    onClick={() => handleGrantCredits(org.id)}
                  >
                    {grantingId === org.id ? "..." : `+ ${adminMessage(lang, "Credits")}`}
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
