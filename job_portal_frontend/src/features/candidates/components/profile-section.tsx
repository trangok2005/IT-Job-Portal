import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export type RunProfileMutation = (
  action: () => Promise<unknown>,
  successMessage: string,
) => Promise<boolean>;

export function ProfileSection({
  id,
  icon: Icon,
  title,
  description,
  action,
  children,
  className,
}: {
  id: string;
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      id={id}
      className={cn(
        "scroll-mt-24 rounded-xl border border-zinc-200 bg-white shadow-[0_8px_28px_rgba(15,76,129,0.06)]",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 px-4 py-4 sm:px-6 sm:py-5">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary">
            <Icon className="size-4.5" />
          </span>
          <div>
            <h2 className="font-semibold text-zinc-900 sm:text-lg">{title}</h2>
            <p className="mt-0.5 text-sm leading-5 text-zinc-500">{description}</p>
          </div>
        </div>
        {action}
      </div>
      <div className="p-4 sm:p-6">{children}</div>
    </section>
  );
}

export function EmptySection({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/70 px-4 py-8 text-center text-sm text-zinc-500">
      {children}
    </div>
  );
}

export const fieldClassName =
  "h-11 w-full rounded-xl border border-zinc-300 bg-white px-3.5 text-sm shadow-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:bg-zinc-50";

export const textareaClassName =
  "min-h-28 w-full resize-y rounded-xl border border-zinc-300 bg-white px-3.5 py-3 text-sm shadow-sm outline-none transition placeholder:text-zinc-400 focus:border-primary focus:ring-2 focus:ring-primary/20";

export function FieldLabel({ children, htmlFor }: { children: React.ReactNode; htmlFor: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-sm font-medium text-zinc-700">
      {children}
    </label>
  );
}
