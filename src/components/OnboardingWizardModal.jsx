import React, { useState } from "react"
import { Sparkles, ArrowRight, CheckCircle2, Search, Compass, Target, Rocket, X } from "lucide-react"
import { accountService } from "../services"

const INDUSTRY_RECOMMENDATIONS = {
  "ecommerce": {
    label: "E-commerce & DTC",
    brands: ["Shopify", "Gymshark", "Glossier", "Allbirds", "Ridge Wallet", "Olaplex"],
    keywords: ["Nike", "Lululemon", "Warby Parker", "Casper"]
  },
  "saas": {
    label: "SaaS & Digital Apps",
    brands: ["Duolingo", "Notion", "Canva", "Linear", "Figma", "Grammarly"],
    keywords: ["Slack", "Airtable", "Monday.com", "Asana"]
  },
  "health": {
    label: "Health & Wellness",
    brands: ["Athletic Greens", "Hims", "Whoop", "Calm", "Headspace", "Oura"],
    keywords: ["Ritual", "Liquid I.V.", "AG1", "Peloton"]
  },
  "fashion": {
    label: "Fashion & Apparel",
    brands: ["Nike", "Zara", "Shein", "Lululemon", "Alo Yoga", "Gymshark"],
    keywords: ["Adidas", "Gymshark", "ASOS", "Uniqlo"]
  },
  "finance": {
    label: "Fintech & Finance",
    brands: ["Revolut", "Wise", "Robinhood", "Klarna", "Stripe", "Coinbase"],
    keywords: ["Chime", "Monzo", "Square", "PayPal"]
  },
  "education": {
    label: "Education & Coaching",
    brands: ["MasterClass", "Coursera", "Babbel", "Udemy", "Skillshare", "Duolingo"],
    keywords: ["Brilliant", "Codecademy", "Khan Academy", "edX"]
  }
}

const GOALS = [
  { id: "hooks", label: "Find Winning Hooks & Angles", icon: Sparkles, desc: "Extract high-converting creative patterns" },
  { id: "generate", label: "Generate Media & Remixes Fast", icon: Rocket, desc: "Turn competitor ads into fresh UGC & studio visuals" },
  { id: "track", label: "Monitor Competitor Ad Spend", icon: Target, desc: "Track ad longevity and active Meta campaigns" }
]

export function OnboardingWizardModal({ isOpen, onClose, onDismiss, onDashboard, onSearchSelect }) {
  const [step, setStep] = useState(1)
  const [selectedIndustry, setSelectedIndustry] = useState("ecommerce")
  const [competitorText, setCompetitorText] = useState("")
  const [selectedGoal, setSelectedGoal] = useState("hooks")
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isOpen) return null

  const handleFinish = (searchQuery = null) => {
    onClose(searchQuery)
    if (searchQuery && onSearchSelect) {
      onSearchSelect(searchQuery)
    }
  }

  const recommendations = INDUSTRY_RECOMMENDATIONS[selectedIndustry] || INDUSTRY_RECOMMENDATIONS["ecommerce"]

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Onboarding"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header Progress Bar */}
        <div className="h-1.5 w-full bg-slate-800">
          <div
            className="h-full bg-gradient-to-r from-teal-500 to-indigo-500 transition-all duration-300"
            style={{ width: `${(step / 3) * 100}%` }}
          />
        </div>

        {/* Modal Close — declining onboarding must not queue the tour */}
        <button
          onClick={() => onDismiss()}
          aria-label="Dismiss onboarding"
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Content Area */}
        <div className="p-8">
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-teal-500/10 text-teal-400 border border-teal-500/20">
                  <Compass className="w-3.5 h-3.5" /> Step 1 of 3 • Zero Cost
                </span>
                <h2 className="text-2xl font-bold text-white mt-3">What industry or niche are you operating in?</h2>
                <p className="text-sm text-slate-400 mt-1">We will tailor recommended competitor search queries for your workspace.</p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {Object.entries(INDUSTRY_RECOMMENDATIONS).map(([key, item]) => {
                  const isSelected = selectedIndustry === key
                  return (
                    <button
                      key={key}
                      onClick={() => setSelectedIndustry(key)}
                      className={`p-3.5 rounded-xl border text-left transition-all ${
                        isSelected
                          ? "bg-teal-500/10 border-teal-500/50 text-white ring-1 ring-teal-500/40"
                          : "bg-slate-800/40 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-800/80"
                      }`}
                    >
                      <div className="font-semibold text-sm">{item.label}</div>
                      <div className="text-xs text-slate-400 mt-1 truncate">{item.brands.slice(0, 2).join(", ")}</div>
                    </button>
                  )
                })}
              </div>

              <div className="flex justify-end pt-4 border-t border-slate-800">
                <button
                  onClick={() => setStep(2)}
                  className="px-5 py-2.5 rounded-xl font-semibold text-sm bg-teal-500 hover:bg-teal-400 text-slate-950 flex items-center gap-2 transition"
                >
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <Target className="w-3.5 h-3.5" /> Step 2 of 3
                </span>
                <h2 className="text-2xl font-bold text-white mt-3">What is your primary growth goal?</h2>
                <p className="text-sm text-slate-400 mt-1">Select the main outcome you want to unlock with Helix.</p>
              </div>

              <div className="space-y-3">
                {GOALS.map((goal) => {
                  const Icon = goal.icon
                  const isSelected = selectedGoal === goal.id
                  return (
                    <button
                      key={goal.id}
                      onClick={() => setSelectedGoal(goal.id)}
                      className={`w-full p-4 rounded-xl border text-left flex items-start gap-4 transition-all ${
                        isSelected
                          ? "bg-indigo-500/10 border-indigo-500/50 text-white ring-1 ring-indigo-500/40"
                          : "bg-slate-800/40 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-800/80"
                      }`}
                    >
                      <div className={`p-2.5 rounded-lg ${isSelected ? "bg-indigo-500 text-white" : "bg-slate-800 text-slate-400"}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div className="flex-1">
                        <div className="font-semibold text-sm">{goal.label}</div>
                        <div className="text-xs text-slate-400 mt-0.5">{goal.desc}</div>
                      </div>
                      {isSelected && <CheckCircle2 className="w-5 h-5 text-indigo-400" />}
                    </button>
                  )
                })}
              </div>

              <div className="flex justify-between pt-4 border-t border-slate-800">
                <button
                  onClick={() => setStep(1)}
                  className="px-4 py-2 rounded-xl text-sm text-slate-400 hover:text-white transition"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep(3)}
                  className="px-5 py-2.5 rounded-xl font-semibold text-sm bg-indigo-500 hover:bg-indigo-400 text-white flex items-center gap-2 transition"
                >
                  Generate Recommendations <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6">
              <div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Workspace Configured • Zero AI Cost
                </span>
                <h2 className="text-2xl font-bold text-white mt-3">Recommended Competitor Lookups</h2>
                <p className="text-sm text-slate-400 mt-1">
                  Click any verified brand to immediately launch a live competitive scrape, or explore your dashboard freely.
                </p>
              </div>

              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Top Brands in {recommendations.label}</div>
                <div className="flex flex-wrap gap-2">
                  {recommendations.brands.map((brand) => (
                    <button
                      key={brand}
                      onClick={() => handleFinish(brand)}
                      className="px-4 py-2.5 rounded-xl bg-slate-800/80 hover:bg-teal-500/20 border border-slate-700 hover:border-teal-500/40 text-slate-200 hover:text-teal-300 font-medium text-sm flex items-center gap-2 transition group"
                    >
                      <Search className="w-3.5 h-3.5 text-slate-400 group-hover:text-teal-400" />
                      {brand}
                      <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Target Creative Angles</div>
                <div className="flex flex-wrap gap-2">
                  {recommendations.keywords.map((kw) => (
                    <button
                      key={kw}
                      onClick={() => handleFinish(kw)}
                      className="px-3.5 py-2 rounded-lg bg-slate-800/40 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-white text-xs transition"
                    >
                      "{kw}"
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex justify-between items-center pt-4 border-t border-slate-800">
                <button
                  onClick={() => setStep(2)}
                  className="px-4 py-2 rounded-xl text-sm text-slate-400 hover:text-white transition"
                >
                  Back
                </button>
                <button
                  onClick={() => onDashboard()}
                  disabled={isSubmitting}
                  className="px-5 py-2.5 rounded-xl font-semibold text-sm bg-slate-800 hover:bg-slate-700 text-white transition"
                >
                  Go to Dashboard
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default OnboardingWizardModal
