import { cn } from "@/lib/utils"

export function Label({ className, children, ...props }) {
  return (
    <label className={cn("label-mono block", className)} {...props}>
      {children}
    </label>
  )
}

export function Input({ className, ...props }) {
  return (
    <input
      className={cn(
        "h-8 w-full min-w-0 rounded-sm border border-border bg-surface-2 px-2.5",
        "text-[13px] text-text placeholder:text-text-faint",
        "transition-colors focus:border-border-strong focus:outline-none",
        "disabled:opacity-40",
        className,
      )}
      {...props}
    />
  )
}

export function Select({ className, options = [], ...props }) {
  return (
    <div className="relative">
      <select
        className={cn(
          "h-8 w-full appearance-none rounded-sm border border-border bg-surface-2 pl-2.5 pr-7",
          "text-[13px] text-text transition-colors",
          "focus:border-border-strong focus:outline-none",
          className,
        )}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <svg
        className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-text-muted"
        viewBox="0 0 12 12"
        fill="none"
        aria-hidden="true"
      >
        <path d="M3 4.5 6 7.5 9 4.5" stroke="currentColor" strokeWidth="1.2" />
      </svg>
    </div>
  )
}

/** Square checkbox — a filter is a switch, not a decoration. */
export function Checkbox({ checked, onChange, label, count, className, ...props }) {
  return (
    <label
      className={cn(
        "group flex cursor-pointer select-none items-center gap-2 py-1",
        className,
      )}
    >
      <span
        className={cn(
          "flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-[2px] border transition-colors",
          checked
            ? "border-accent bg-accent"
            : "border-border-strong bg-surface-2 group-hover:border-text-faint",
        )}
      >
        {checked ? (
          <svg viewBox="0 0 10 10" className="h-2.5 w-2.5 text-[#0A0A0A]" aria-hidden="true">
            <path
              d="M1.5 5.2 3.8 7.5 8.5 2.8"
              stroke="currentColor"
              strokeWidth="1.6"
              fill="none"
              strokeLinecap="square"
            />
          </svg>
        ) : null}
      </span>
      <input
        type="checkbox"
        className="sr-only"
        checked={checked}
        onChange={onChange}
        {...props}
      />
      <span
        className={cn(
          "flex-1 truncate text-[13px] transition-colors",
          checked ? "text-text" : "text-text-muted group-hover:text-text",
        )}
      >
        {label}
      </span>
      {count !== undefined ? (
        <span className="tnum font-mono text-[10px] text-text-faint">{count}</span>
      ) : null}
    </label>
  )
}
