import { useEffect, useRef } from "react"

export function OnboardingTour({ user, enabled = true, onComplete }) {
  const onCompleteRef = useRef(onComplete)
  useEffect(() => { onCompleteRef.current = onComplete }, [onComplete])
  const eligible = enabled && !!user && !user.has_completed_onboarding

  useEffect(() => {
    if (!eligible) return
    let cancelled = false
    let completed = false
    let tour = null
    let timer

    // Neither the driver bundle nor its stylesheet loads for returning users.
    Promise.all([import("driver.js"), import("driver.js/dist/driver.css")]).then(([{ driver }]) => {
      if (cancelled) return
      tour = driver({
      animate: !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches,
      showProgress: true,
      showButtons: ["next", "previous", "close"],
      popoverClass: "helixa-driver-theme",
      onDestroyStarted: () => {
        tour.destroy()
        if (cancelled || completed) return
        completed = true
        Promise.resolve().then(() => onCompleteRef.current?.()).catch(err => {
          console.error("Failed to complete onboarding:", err)
        })
      },
      steps: [
        {
          element: '#tour-discover-nav',
          popover: {
            title: 'Welcome to Helix Intelligence',
            description: "This is where you'll research any competitor's ads and market campaigns.",
            side: "right",
            align: 'start'
          }
        },
        {
          element: '#tour-search-input',
          popover: {
            title: 'Search any competitor or brand',
            description: "Type a brand name (e.g. Shopify, Duolingo, Nike) to pull live active ads.",
            side: "bottom",
            align: 'start'
          }
        },
        {
          element: '#tour-job-progress',
          popover: {
            title: 'Real-Time Scrape Progress',
            description: "Watch live provider progress and instant domain deduction metering.",
            side: "bottom",
            align: 'start'
          }
        },
        {
          element: '#tour-results-area',
          popover: {
            title: 'Deep Creative Intelligence',
            description: "Inspect winning hook formulas, extract patterns, and remix straight into Create Studio.",
            side: "top",
            align: 'start'
          }
        }
      ]
    })

      // Give the Discover elements time to mount, and cancel stale imports/timers.
      timer = setTimeout(() => { if (!cancelled) tour.drive() }, 400)
    }).catch(err => {
      if (!cancelled) console.error("Failed to load onboarding:", err)
    })

    return () => {
      cancelled = true
      clearTimeout(timer)
      tour?.destroy()
    }
  }, [eligible, user?.id])

  return null
}
