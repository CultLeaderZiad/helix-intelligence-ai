import React, { useState, useRef } from "react"
import { User, Lock, Camera, CheckCircle2, AlertCircle, Save, Shield, Eye, EyeOff, RotateCcw } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { useLanguage } from "../context/LanguageContext"
import { BreadcrumbBar } from "@/app/BreadcrumbBar"
import { getW5OnboardingText } from "../i18n/w5Onboarding"
import { getMemberMessage, getMemberRoleLabel } from "@/i18n/memberMessages"
import { useProfileSettings } from "@/hooks/useProfileSettings"

export function ProfileSettingsPage() {
  const { user, signOut, refreshSession, updateUser } = useAuth()
  const navigate = useNavigate()
  const { lang, t } = useLanguage()
  const {
    profile,
    setProfile,
    isLoadingProfile,
    loadError,
    isSaving,
    isUploadingAvatar,
    uploadAvatar,
    saveProfile,
    restartOnboarding,
  } = useProfileSettings()
  const fileInputRef = useRef(null)
  const [isRestartingTour, setIsRestartingTour] = useState(false)

  const text = (key) => t(key, getMemberMessage(lang, key))
  const onboardingText = (key) => t(key, getW5OnboardingText(lang, key))
  const canMutateAccount = Boolean(user?.organization_id)

  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [successMessage, setSuccessMessage] = useState("")
  const [errorMessage, setErrorMessage] = useState("")

  const handleAvatarChange = async (e) => {
    const input = e.currentTarget
    const file = input.files?.[0]
    if (!file) return
    if (!canMutateAccount) {
      setErrorMessage(text("profileWorkspaceAssignmentRequired"))
      return
    }

    setErrorMessage("")
    setSuccessMessage("")

    try {
      const res = await uploadAvatar(file)
      if (!res?.avatar_url) throw new Error("avatar_url_missing")
      setSuccessMessage(text("profileAvatarUpdated"))
      if (refreshSession) refreshSession()
    } catch {
      setErrorMessage(text("profileAvatarUploadFailed"))
    } finally {
      input.value = ""
    }
  }

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setErrorMessage("")
    setSuccessMessage("")

    if (!canMutateAccount) {
      setErrorMessage(text("profileWorkspaceAssignmentRequired"))
      return
    }

    if (newPassword) {
      if (!currentPassword) {
        setErrorMessage(text("profileCurrentPasswordRequired"))
        return
      }
      if (newPassword.length < 8) {
        setErrorMessage(text("profilePasswordTooShort"))
        return
      }
      if (newPassword !== confirmPassword) {
        setErrorMessage(text("profilePasswordMismatch"))
        return
      }
    }

    try {
      const passwordChanged = Boolean(newPassword)
      await saveProfile({
        fullName: profile.full_name,
        avatarUrl: profile.avatar_url,
        currentPassword,
        newPassword,
      })
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      if (passwordChanged) {
        await signOut()
        navigate("/sign-in", {
          replace: true,
          state: { email: profile.email, passwordChanged: true },
        })
        return
      }
      setSuccessMessage(text("profileUpdated"))
      if (refreshSession) refreshSession()
    } catch {
      setErrorMessage(text("profileUpdateFailed"))
    }
  }

  const handleRestartTour = async () => {
    setErrorMessage("")
    setSuccessMessage("")
    setIsRestartingTour(true)
    try {
      await restartOnboarding()
      if (refreshSession) await refreshSession()
      updateUser?.({ has_completed_onboarding: false })
      navigate("/discover?tour=restart")
    } catch {
      setErrorMessage(onboardingText("w5_settings_tour_error"))
    } finally {
      setIsRestartingTour(false)
    }
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 font-sans" dir={lang === "ar" ? "rtl" : "ltr"}>
      <BreadcrumbBar trail={["Helix", text("settingsNavigation"), text("profileAccountBreadcrumb")]} meta={null} actions={null} className="" />
      <div className="w-full max-w-4xl mx-auto p-4 md:p-8 space-y-8 font-sans">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">{text("profileSettingsTitle")}</h1>
        <p className="text-sm text-slate-400 mt-1">
          {text("profileSettingsDescription")}
        </p>
      </div>

      {isLoadingProfile && <div role="status" className="text-sm text-slate-400">{text("loadingProfile")}</div>}
      {loadError && <div role="alert" className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">{text("profileLoadFailed")}</div>}
      {!canMutateAccount && <div role="status" className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-300 text-sm">{text("profileWorkspaceAssignmentRequired")}</div>}

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
                <img src={profile.avatar_url} alt={text("profilePhoto")} className="w-full h-full object-cover" />
              ) : (
                <User className="w-10 h-10 text-slate-500" />
              )}
            </div>
            {canMutateAccount && <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploadingAvatar || isLoadingProfile || loadError}
              className="absolute inset-0 rounded-2xl bg-slate-950/70 text-white flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition duration-200 cursor-pointer"
            >
              <Camera className="w-6 h-6 mb-1" />
              <span className="text-[10px] font-semibold">{text("changePhoto")}</span>
            </button>}
            {canMutateAccount && <input
              type="file"
              ref={fileInputRef}
              onChange={handleAvatarChange}
              accept="image/*"
              disabled={isUploadingAvatar || isLoadingProfile || loadError}
              className="hidden"
            />}
          </div>

          <div className="space-y-1 text-center sm:text-left">
            <h3 className="font-semibold text-white text-base">{text("profilePhoto")}</h3>
            {canMutateAccount && <p className="text-xs text-slate-400">
              {text("photoUploadGuidance")}
            </p>}
            {canMutateAccount && <div className="pt-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingAvatar || isLoadingProfile || loadError}
                className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
              >
                {isUploadingAvatar ? text("uploadingPhoto") : text("uploadPhoto")}
              </button>
            </div>}
          </div>
        </div>

        {/* Profile Info Section */}
        <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <User className="w-4 h-4 text-teal-400" /> {text("personalInformation")}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="profile-full-name" className="block text-xs font-medium text-slate-300 mb-1.5">{text("fullName")}</label>
              <input
                id="profile-full-name"
                type="text"
                value={profile.full_name}
                disabled={!canMutateAccount}
                onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                placeholder={text("fullNamePlaceholder")}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-teal-500/60 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">{text("emailAddress")}</label>
              <input
                type="email"
                disabled
                value={profile.email}
                className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-800/60 rounded-xl text-slate-400 text-sm cursor-not-allowed"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">{text("workspaceEmailDescription")}</span>
            </div>
          </div>

          <div className="pt-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 text-xs text-slate-300">
              <Shield className="w-3.5 h-3.5 text-teal-400" /> {text("roleLabel")}: <span className="font-semibold text-white">{getMemberRoleLabel(lang, profile.role)}</span>
            </div>
          </div>
        </div>

        {/* Security / Password Section */}
        {canMutateAccount && <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Lock className="w-4 h-4 text-indigo-400" /> {text("changePassword")}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">{text("currentPassword")}</label>
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
                  aria-label={text(showCurrentPassword ? "hideCurrentPassword" : "showCurrentPassword")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-slate-300 transition"
                >
                  {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">{text("newPassword")}</label>
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
                  aria-label={text(showNewPassword ? "hideNewPassword" : "showNewPassword")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-slate-300 transition"
                >
                  {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">{text("confirmNewPassword")}</label>
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
                  aria-label={text(showConfirmPassword ? "hideConfirmPassword" : "showConfirmPassword")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-500 hover:text-slate-300 transition"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>
        </div>}

        {/* Save Actions */}
        {canMutateAccount && <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={isSaving || isLoadingProfile || loadError}
            className="px-6 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-slate-950 font-semibold text-sm flex items-center gap-2 transition shadow-lg shadow-teal-500/10"
          >
            <Save className="w-4 h-4" /> {isSaving ? text("savingChanges") : text("saveSettings")}
          </button>
        </div>}
      </form>
      </div>
    </div>
  )
}

export default ProfileSettingsPage
