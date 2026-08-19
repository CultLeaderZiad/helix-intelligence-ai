import { PublicHeader } from "@/app/PublicHeader"
import { Hero } from "@/features/marketing/Hero"
import { LoopsSection } from "@/features/marketing/LoopsSection"
import { PricingSection } from "@/features/marketing/PricingSection"
import { DocsSection } from "@/features/marketing/DocsSection"
import { MarketingFooter } from "@/features/marketing/MarketingFooter"

/**
 * ============================================================
 * LANDING — the public front door at "/"
 * ============================================================
 * The site's only fully public surface. It shares the pre-auth chrome
 * (PublicHeader / footer) with the auth pages, and its sections carry the
 * ids the header nav already points at (#product, #pricing, #docs) so those
 * links finally resolve. Nothing here is gated: visitors reach the auth
 * pages only by choosing Sign in / Get started.
 * ============================================================
 */
export function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <PublicHeader />
      <main className="flex-1">
        <Hero />
        <LoopsSection />
        <PricingSection />
        <DocsSection />
      </main>
      <MarketingFooter />
    </div>
  )
}
