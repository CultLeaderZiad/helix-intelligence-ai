import { cn } from "@/lib/utils"
import { Label } from "@/components/ui/Field"

/**
 * A labelled form row for the auth surfaces. Reuses the app's mono `Label`
 * and hosts the field-level error in the label row (right-aligned, mono,
 * danger) so an error never reflows the layout by appearing below. The
 * optional `action` slot carries an inline control like a "forgot?" link.
 *
 * The input itself is the shared `Input` primitive, passed as children so
 * this wrapper stays agnostic about type/autocomplete/etc.
 */
export function AuthField({ id, label, error, action, children, className }) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-baseline justify-between gap-2">
        <Label htmlFor={id}>{label}</Label>
        {error ? (
          <span
            id={`${id}-error`}
            className="font-mono text-[10px] uppercase leading-none tracking-[0.08em] text-danger"
          >
            {error}
          </span>
        ) : action ? (
          action
        ) : null}
      </div>
      {children}
    </div>
  )
}
