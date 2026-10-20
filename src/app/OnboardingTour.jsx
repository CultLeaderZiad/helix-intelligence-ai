import { useEffect, useRef, useState } from "react"
import { useLanguage } from "../context/LanguageContext"
import {
  getW5OnboardingText,
  ONBOARDING_TOUR_RESTART_EVENT,
} from "../i18n/w5Onboarding"

function isVisibleTarget(selector) {
  const element = document.querySelector(selector)
  if (!(element instanceof HTMLElement) || element.closest("[hidden], [aria-hidden='true']")) {
    return false
  }

  for (let current = element; current instanceof HTMLElement; current = current.parentElement) {
    const style = window.getComputedStyle(current)
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") {
      return false
    }
  }

  const rect = element.getBoundingClientRect()
  return rect.width > 0 && rect.height > 0
}

export function OnboardingTour({ user, enabled = true, onComplete }) {
  const { lang, t } = useLanguage()
  const [restartRequested, setRestartRequested] = useState(false)
  const onCompleteRef = useRef(onComplete)
  const finishedUserIdRef = useRef(null)
  const translateRef = useRef(null)
  onCompleteRef.current = onComplete
  translateRef.current = (key) => t(key, getW5OnboardingText(lang, key))

  useEffect(() => {
    const requestRestart = (event) => {
      if (event.detail?.persisted !== true) return
      finishedUserIdRef.current = null
      setRestartRequested(true)
    }
    window.addEventListener(ONBOARDING_TOUR_RESTART_EVENT, requestRestart)
    return () => window.removeEventListener(ONBOARDING_TOUR_RESTART_EVENT, requestRestart)
  }, [])

  const eligible =
    !!user &&
    finishedUserIdRef.current !== user.id &&
    (restartRequested || (enabled && !user.has_completed_onboarding))

  useEffect(() => {
    if (!eligible) return undefined

    let cancelled = false
    let completed = false
    let tour = null
    let timer
    const originalBodyOverflow = document.body.style.overflow
    const translate = (key) => translateRef.current(key)

    const restoreBodyOverflow = () => {
      document.body.style.overflow = originalBodyOverflow
    }

    Promise.all([import("driver.js"), import("driver.js/dist/driver.css")]).then(([{ driver }]) => {
      if (cancelled) return

      const steps = [
        {
          element: "#tour-discover-nav",
          popover: {
            title: translate("w5_tour_discover_title"),
            description: translate("w5_tour_discover_description"),
            side: lang === "ar" ? "left" : "right",
            align: "start",
          },
        },
        {
          element: "#tour-search-input",
          popover: {
            title: translate("w5_tour_search_title"),
            description: translate("w5_tour_search_description"),
            side: "bottom",
            align: "start",
          },
        },
        {
          element: "#tour-results-area",
          popover: {
            title: translate("w5_tour_results_title"),
            description: translate("w5_tour_results_description"),
            side: "top",
            align: "start",
          },
        },
      ].filter((step) => isVisibleTarget(step.element))

      if (!steps.length) return

      tour = driver({
        animate: !(window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false),
        showProgress: true,
        showButtons: ["next", "previous", "close"],
        popoverClass: "helixa-driver-theme",
        steps,
        onDestroyStarted: () => {
          if (cancelled || completed) return
          completed = true
          finishedUserIdRef.current = user?.id
          try {
            tour?.destroy()
          } finally {
            restoreBodyOverflow()
            setRestartRequested(false)
          }
          Promise.resolve()
            .then(() => onCompleteRef.current?.())
            .catch((error) => console.error("Failed to complete onboarding:", error))
        },
      })

      timer = setTimeout(() => {
        if (!cancelled) tour?.drive()
      }, 250)
    }).catch((error) => {
      if (!cancelled) console.error("Failed to load onboarding:", error)
    })

    return () => {
      cancelled = true
      clearTimeout(timer)
      try {
        tour?.destroy()
      } finally {
        restoreBodyOverflow()
      }
    }
  }, [eligible, lang, restartRequested, user?.id])

  return null
}
