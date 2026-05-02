import * as React from "react";
import { cn } from "@/lib/utils";

export const Button = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "ghost" | "danger" }
>(({ className, variant = "default", ...props }, ref) => {
  const base =
    "inline-flex items-center justify-center rounded-md text-sm font-medium px-4 py-2 transition-colors disabled:opacity-50 disabled:pointer-events-none";
  const styles = {
    default: "bg-zinc-900 text-white hover:bg-zinc-800",
    ghost: "bg-transparent hover:bg-zinc-100 text-zinc-900",
    danger: "bg-red-600 text-white hover:bg-red-700",
  }[variant];
  return <button ref={ref} className={cn(base, styles, className)} {...props} />;
});
Button.displayName = "Button";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900",
      className,
    )}
    {...props}
  />
));
Input.displayName = "Input";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-lg border border-zinc-200 bg-white shadow-sm", className)}
      {...props}
    />
  );
}
