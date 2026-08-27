import { useEffect, useRef } from "react"
import { driver } from "driver.js"
import "driver.js/dist/driver.css"
export function OnboardingTour({ user, onComplete }) {
  const driverObj = useRef(null)

  useEffect(() => {
    if (!user || user.has_completed_onboarding) return

    const handleComplete = async () => {
      try {
        onComplete && onComplete()
      } catch (err) {
        console.error("Failed to complete onboarding:", err)
      }
    }

    driverObj.current = driver({
      showProgress: true,
      showButtons: ["next", "previous", "close"],
      popoverClass: "helixa-driver-theme",
      onDestroyStarted: () => {
        if (!driverObj.current.hasNextStep() || confirm("Are you sure you want to skip the tour?")) {
          driverObj.current.destroy()
          handleComplete()
        }
      },
      steps: [
        {
          element: '#tour-discover-nav',
          popover: {
            title: 'Welcome to Helix Intelligence',
            description: "This is where you'll research any competitor's ads.",
            side: "right",
            align: 'start'
          }
        },
        {
          element: '#tour-search-input',
          popover: {
            title: 'Start your search',
            description: "Type a brand name and hit search — try a well-known brand first.",
            side: "bottom",
            align: 'start'
          }
        },
        {
          element: '#tour-job-progress',
          popover: {
            title: 'Live Tracking',
            description: "You'll see it search in real time here.",
            side: "bottom",
            align: 'start'
          }
        },
        {
          element: '#tour-results-area',
          popover: {
            title: 'Deep Analysis',
            description: "Once results load, click Analyze on any ad to see why it works.",
            side: "top",
            align: 'start'
          }
        }
      ]
    })

    // Slight delay to ensure DOM elements are rendered
    setTimeout(() => {
      driverObj.current.drive()
    }, 500)

    return () => {
      if (driverObj.current) {
        driverObj.current.destroy()
      }
    }
  }, [user, onComplete])

  return null
}
