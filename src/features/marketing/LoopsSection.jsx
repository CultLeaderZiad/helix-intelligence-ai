import { Compass, Cpu, Layers } from "lucide-react"
import { useLanguage } from "@/context/LanguageContext"

export function LoopsSection() {
  const { t } = useLanguage()
  const capabilities = [
    { title: t("marketingDiscoverTitle"), description: t("marketingDiscoverBody"), Icon: Compass },
    { title: t("marketingCreativeTitle"), description: t("marketingCreativeBody"), Icon: Cpu },
    { title: t("marketingWorkspaceTitle"), description: t("marketingWorkspaceBody"), Icon: Layers },
  ]

  return (
    <section id="product" className="bg-[#09090d] px-6 py-20 text-white sm:px-8 sm:py-24 lg:px-12">
      <div className="mx-auto max-w-7xl">
        <div className="max-w-2xl">
          <p className="font-mono text-xs uppercase tracking-widest text-accent">{t("marketingCapabilitiesLabel")}</p>
          <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">{t("marketingCapabilities")}</h2>
          <p className="mt-4 text-sm leading-6 text-text-muted">{t("marketingCapabilitiesIntro")}</p>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {capabilities.map(({ title, description, Icon }) => (
            <article key={title} className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-6">
              <Icon className="h-5 w-5 text-accent" aria-hidden="true" />
              <h3 className="mt-5 text-lg font-semibold">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-text-muted">{description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

export default LoopsSection
