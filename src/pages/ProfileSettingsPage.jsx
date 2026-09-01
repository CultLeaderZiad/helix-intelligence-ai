import React, { useState, useEffect, useRef } from "react"
import { User, Mail, Lock, Camera, CheckCircle2, AlertCircle, Save, Shield } from "lucide-react"
import { accountService } from "../services"
import { useAuth } from "../context/AuthContext"

export function ProfileSettingsPage() {
  const { user, refreshSession } = useAuth()
  const fileInputRef = useRef(null)

  const [profile, setProfile] = useState({
    full_name: "",
    email: "",
    avatar_url: "",
    role: "customer"
  })
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  
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
      setSuccessMessage("Profile picture updated successfully!")
      if (refreshSession) refreshSession()
    } catch (err) {
      setErrorMessage(err?.message || "Failed to upload avatar image")
    } finally {
      setIsUploadingAvatar(false)
    }
  }

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setErrorMessage("")
    setSuccessMessage("")

    if (newPassword && newPassword !== confirmPassword) {
      setErrorMessage("New passwords do not match")
      return
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
      setSuccessMessage("Profile updated successfully!")
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      if (refreshSession) refreshSession()
    } catch (err) {
      setErrorMessage(err?.message || "Failed to update profile")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Account & Profile Settings</h1>
        <p className="text-sm text-slate-400 mt-1">
          Manage your personal details, avatar, and account security.
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

      {/* Form Container */}
      <form onSubmit={handleSaveProfile} className="space-y-6">
        {/* Avatar Section */}
        <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-col sm:flex-row items-center gap-6">
          <div className="relative group">
            <div className="w-24 h-24 rounded-2xl bg-slate-800 border-2 border-slate-700 overflow-hidden flex items-center justify-center">
              {profile.avatar_url ? (
                <img src={profile.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
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
              <span className="text-[10px] font-semibold">Change</span>
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
            <h3 className="font-semibold text-white text-base">Profile Photo</h3>
            <p className="text-xs text-slate-400">
              Upload a PNG, JPG, or WebP image. Max size 5MB.
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingAvatar}
                className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
              >
                {isUploadingAvatar ? "Uploading..." : "Upload New Photo"}
              </button>
            </div>
          </div>
        </div>

        {/* Profile Info Section */}
        <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <User className="w-4 h-4 text-teal-400" /> Personal Information
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Full Name</label>
              <input
                type="text"
                value={profile.full_name}
                onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                placeholder="e.g. John Doe"
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-teal-500/60 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Email Address</label>
              <input
                type="email"
                disabled
                value={profile.email}
                className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-800/60 rounded-xl text-slate-400 text-sm cursor-not-allowed"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">Account email linked to your workspace.</span>
            </div>
          </div>

          <div className="pt-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 text-xs text-slate-300">
              <Shield className="w-3.5 h-3.5 text-teal-400" /> Role: <span className="font-semibold uppercase text-white">{profile.role}</span>
            </div>
          </div>
        </div>

        {/* Security / Password Section */}
        <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Lock className="w-4 h-4 text-indigo-400" /> Change Password
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Current Password</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Confirm New Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder:text-slate-600 text-sm focus:outline-none focus:border-indigo-500/60 transition"
              />
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
            <Save className="w-4 h-4" /> {isSaving ? "Saving Changes..." : "Save Settings"}
          </button>
        </div>
      </form>
    </div>
  )
}

export default ProfileSettingsPage
