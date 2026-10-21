import React, { useState, useEffect, useRef } from "react"
import { User, Lock, Camera, CheckCircle2, AlertCircle, Save, Shield, Eye, EyeOff, RotateCcw } from "lucide-react"
import { accountService, authService } from "../services"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { useLanguage } from "../context/LanguageContext"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { getW5OnboardingText } from "../i18n/w5Onboarding"

export function ProfileSettingsPage() {
  const { refreshSession, updateUser } = useAuth()
  const navigate = useNavigate()
  const { lang, t } = useLanguage()
  const fileInputRef = useRef(null)
  const [isRestartingTour, setIsRestartingTour] = useState(false)

  const onboardingText = (key) => t(key, getW5OnboardingText(lang, key))

  const [profile, setProfile] = useState({
    full_name: "",
    email: "",
    avatar_url: "",
    role: "customer"
  })
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  
  const [isSaving, setIsSaving] = useState(false)
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false)
  const [successMessage, setSuccessMessage] = useState("")
  const [errorMessage, setErrorMessage] = useState("")

  const loadProfile = async () => {
    try {
      const data = await accountService.getProfile()
      setProfile({
        full_name: data.full_name || "",
        email: data.email || "",
        avatar_url: data.avatar_url || "",
        role: data.role || "customer"
      })
    } catch (err) {
      console.error("Failed to load profile:", err)
    }
  }

  useEffect(() => {
    loadProfile()
  }, [])

  const handleAvatarChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploadingAvatar(true)
    setErrorMessage("")
    setSuccessMessage("")

    try {
      const res = await accountService.uploadAvatar(file)
      setProfile((prev) => ({ ...prev, avatar_url: res.avatar_url }))
      setSuccessMessage(t("profileAvatarUpdated"))
      if (refreshSession) refreshSession()
    } catch (err) {
      setErrorMessage(err?.message || t("profileAvatarUploadFailed"))
    } finally {
      setIsUploadingAvatar(false)
    }
  }

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setErrorMessage("")
    setSuccessMessage("")

    if (newPassword) {
      if (!currentPassword) {
        setErrorMessage(t("profileCurrentPasswordRequired"))
        return
      }
      if (newPassword.length < 8) {
        setErrorMessage(t("profilePasswordTooShort"))
        return
      }
      if (newPassword !== confirmPassword) {
        setErrorMessage(t("profilePasswordMismatch"))
        return
      }
    }

    setIsSaving(true)
    try {
      const payload = {
        full_name: profile.full_name,
        avatar_url: profile.avatar_url,
      }
      if (newPassword) {
        payload.current_password = currentPassword
        payload.new_password = newPassword
      }

      await accountService.updateProfile(payload)
      setSuccessMessage(t("profileUpdated"))
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      if (refreshSession) refreshSession()
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || "Failed to update profile."
      setErrorMessage(typeof detail === "string" ? detail : t("profileUpdateFailed"))
    } finally {
      setIsSaving(false)
    }
  }

  const handleRestartTour = async () => {
    setErrorMessage("")
    setSuccessMessage("")
    setIsRestartingTour(true)
    try {
      await authService.restartOnboarding()
      if (refreshSession) await refreshSession()
      updateUser?.({ has_completed_onboarding: false })
      navigate("/discover?tour=restart")
    } catch (error) {
      setErrorMessage(error?.message || onboardingText("w5_settings_tour_error"))
    } finally {
      setIsRestartingTour(false)
    }
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 font-sans">
      <BreadcrumbBar trail={["Helix", t("settingsNavigation", "Settings"), t("profileAccountBreadcrumb", "Account & profile")]} meta={null} actions={null} className="" />
      <div className="w-full max-w-4xl mx-auto p-4 md:p-8 space-y-8 font-sans">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">{t("profileSettingsTitle", "Account & profile settings")}</h1>
        <p className="text-sm text-slate-400 mt-1">
          {t("profileSettingsDescription", "Manage your personal details, profile photo, and account security.")}
        </p>
      </div>

      {/* Alerts */}
      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 shrink-0" />
          {errorMessage}
        </div>
      )}

      <section className="flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-semibold text-white">{onboardingText("w5_settings_tour_title")}</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">
            {onboardingText("w5_settings_tour_description")}
          </p>
        </div>
        <button
          type="button"
          onClick={handleRestartTour}
          disabled={isRestartingTour}
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg border border-slate-700 px-4 text-sm font-semibold text-slate-100 transition hover:border-teal-500 hover:bg-teal-500/10 disabled:cursor-wait disabled:opacity-60"
        >
          <RotateCcw className={`h-4 w-4 ${isRestartingTour ? "animate-spin" : ""}`} aria-hidden="true" />
          {onboardingText(isRestartingTour ? "w5_settings_tour_restarting" : "w5_settings_tour_restart")}
        </button>
      </section>

      {/* Form Container */}
      <form onSubmit={handleSaveProfile} className="space-y-6">
        {/* Avatar Section */}
        <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-col sm:flex-row items-center gap-6">
          <div className="relative group">
            <div className="w-24 h-24 rounded-2xl bg-slate-800 border-2 border-slate-700 overflow-hidden flex items-center justify-center">
              {profile.avatar_url ? (
                <img src={profile.avatar_url} alt={t("profilePhoto", "Profile photo")} className="w-full h-full object-cover" />
              ) : (
                <User className="w-10 h-10 text-slate-500" />
              )}
            </div>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploadingAvatar}
              className="absolute inset-0 rounded-2xl bg-slate-950/70 text-white flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition duration-200 cursor-pointer"
            >
              <Camera className="w-6 h-6 mb-1" />
              <span className="text-[10px] font-semibold">{t("changePhoto", "Change photo")}</span>
            </button>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleAvatarChange}
              accept="image/*"
              className="hidden"
            />
          </div>

          <div className="space-y-1 text-center sm:text-left">
            <h3 className="font-semibold text-white text-base">{t("profilePhoto", "Profile photo")}</h3>
            <p className="text-xs text-slate-400">
              {t("photoUploadGuidance", "Upload a PNG, JPG, or WebP image. Maximum size: 5 MB.")}
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingAvatar}
                className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
              >
                {isUploadingAvatar ? t("uploadingPhoto", "Uploading…") : t("uploadPhoto", "Upload new photo")}
              </button>
            </div>
          </div>
        </div>

        {/* Profile Info Section */}
        <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <User className="w-4 h-4 text-teal-400" /> {t("personalInformation", "Personal information")}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">{t("fullName", "Full name")}</label>
              <input
                type="text"
                value={profile.full_name}
                onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                placeholder={t("fullNamePlaceholder", "e.g. John Doe")}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-teal-500/60 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">{t("emailAddress", "Email address")}</label>
              <input
                type="email"
                disabled
                value={profile.email}
                className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-800/60 rounded-xl text-slate-400 text-sm cursor-not-allowed"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">{t("workspaceEmailDescription", "Account email linked to your workspace.")}</span>
            </div>
          </div>

          <div className="pt-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 text-xs text-slate-300">
              <Shield className="w-3.5 h-3.5 text-teal-400" /> {t("roleLabel", "Role")}: <span className="font-semibold uppercase text-white">{profile.role}</span>
            </div>
          </div>
        </div>

        {/* Security / Password Section */}
        <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Lock className="w-4 h-4 text-indigo-400" /> {t("changePassword", "Change password")}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">{t("currentPassword", "Current password")}</label>
              <div className="relative">
                <input
                  type={showCurrentPassword ? "text" : "password"}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2.5 pr-9 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  aria-label={t(showCurrentPassword ? "hideCurrentPassword" : "showCurrentPassword")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-slate-300 transition"
                >
                  {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">{t("newPassword", "New password")}</label>
              <div className="relative">
                <input
                  type={showNewPassword ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2.5 pr-9 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  aria-label={t(showNewPassword ? "hideNewPassword" : "showNewPassword")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-slate-300 transition"
                >
                  {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">{t("confirmNewPassword", "Confirm new password")}</label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2.5 pr-9 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  aria-label={t(showConfirmPassword ? "hideConfirmPassword" : "showConfirmPassword")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-slate-300 transition"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Save Actions */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="px-6 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-slate-950 font-semibold text-sm flex items-center gap-2 transition shadow-lg shadow-teal-500/10"
          >
            <Save className="w-4 h-4" /> {isSaving ? t("savingChanges", "Saving changes…") : t("saveSettings", "Save settings")}
          </button>
        </div>
      </form>
      </div>
    </div>
  )
}

export default ProfileSettingsPage
