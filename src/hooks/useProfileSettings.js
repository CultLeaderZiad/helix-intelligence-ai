import { useCallback, useEffect, useState } from "react"
import { accountService, authService } from "@/services"

const emptyProfile = {
  full_name: "",
  email: "",
  avatar_url: "",
  role: "customer",
}

export function useProfileSettings() {
  const [profile, setProfile] = useState(emptyProfile)
  const [isLoadingProfile, setIsLoadingProfile] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false)

  useEffect(() => {
    let active = true

    const loadProfile = async () => {
      setIsLoadingProfile(true)
      setLoadError(false)
      try {
        const data = await accountService.getProfile()
        if (active) {
          setProfile({
            full_name: data?.full_name || "",
            email: data?.email || "",
            avatar_url: data?.avatar_url || "",
            role: data?.role || "customer",
          })
        }
      } catch {
        if (active) setLoadError(true)
      } finally {
        if (active) setIsLoadingProfile(false)
      }
    }

    void loadProfile()
    return () => { active = false }
  }, [])

  const uploadAvatar = useCallback(async (file) => {
    setIsUploadingAvatar(true)
    try {
      const result = await accountService.uploadAvatar(file)
      if (typeof result?.avatar_url === "string") {
        setProfile((previous) => ({ ...previous, avatar_url: result.avatar_url }))
      }
      return result
    } finally {
      setIsUploadingAvatar(false)
    }
  }, [])

  const saveProfile = useCallback(async ({ fullName, avatarUrl, currentPassword = "", newPassword = "" }) => {
    const payload = {
      full_name: fullName || "",
      avatar_url: avatarUrl || "",
    }
    if (newPassword) {
      payload.current_password = currentPassword || ""
      payload.new_password = newPassword
    }

    setIsSaving(true)
    try {
      const result = await accountService.updateProfile(payload)
      setProfile((previous) => ({
        ...previous,
        ...(result && typeof result === "object" ? result : {}),
        full_name: result?.full_name ?? payload.full_name,
        avatar_url: result?.avatar_url ?? payload.avatar_url,
      }))
      return result
    } finally {
      setIsSaving(false)
    }
  }, [])

  const restartOnboarding = useCallback(() => authService.restartOnboarding(), [])

  return {
    profile,
    setProfile,
    isLoadingProfile,
    loadError,
    isSaving,
    isUploadingAvatar,
    uploadAvatar,
    saveProfile,
    restartOnboarding,
  }
}
