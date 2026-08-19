import { cn } from "@/lib/utils"
import { NAV_SECTIONS } from "@/app/navigation"

/**
 * The product, expressed as the four loops that already drive the app's
 * sidebar — read straight from NAV_SECTIONS so marketing can never claim a
 * loop the console does not have. Numbered 01–04 because they are a genuine
 * pipeline (each loop's output is the next loop's input), not decoration.
 */
export function LoopsSection() {
  return (
    <section id="product" className="scroll-mt-16 border-b border-border">
      <div className="mx-auto w-full max-w-6xl px-4 py-20 md:px-6">
        <div className="flex flex-col gap-3 md:max-w-2xl">
          <span className="font-mono text-[10px] uppercase leading-none tracking-[0.14em] text-accent-dim">
            The product
          </span>
          <h2 className="text-balance text-2xl font-medium tracking-tight text-text md:text-3xl">
            Four loops, one instrument.
          </h2>
          <p className="text-pretty text-sm leading-relaxed text-text-muted">
            Discovery feeds intelligence, intelligence briefs creation, and live
            performance feeds back into scoring. The output of each loop is the
            input to the next.
          </p>
        </div>

        <ol className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-sm border border-border bg-border md:grid-cols-2">
          {NAV_SECTIONS.map((section, index) => {
            const Icon = section.icon
            const live = section.status === "live"
            return (
              <li key={section.key} className="flex flex-col gap-4 bg-surface p-6">
                <div className="flex items-center justify-between">
                  <span className="tnum font-mono text-xs text-text-faint">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span
                    className={cn(
                      "label-mono",
                      live ? "text-accent-dim" : "text-text-faint",
                    )}
                  >
                    {live ? "live" : "soon"}
                  </span>
                </div>

                <span className="flex h-8 w-8 items-center justify-center rounded-sm border border-border-strong bg-surface-2">
                  <Icon className="h-4 w-4 text-text" aria-hidden="true" />
                </span>

                <div className="flex flex-col gap-1.5">
                  <h3 className="text-sm font-medium text-text">{section.label}</h3>
                  <p className="text-[13px] leading-relaxed text-text-muted">
                    {section.description}
                  </p>
                </div>
              </li>
            )
          })}
        </ol>
      </div>
    </section>
  )
}
