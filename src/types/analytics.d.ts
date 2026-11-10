interface PlausibleTracker {
  (event: string, options?: { props?: Record<string, string | number>; u?: string }): void
  q?: IArguments[]
}

interface Window {
  plausible?: PlausibleTracker
}
