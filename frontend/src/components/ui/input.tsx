import type { InputHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-10 rounded-md border border-[#f3d2c1] bg-[#fef6e4] px-3 text-sm text-[#001858] outline-none transition-colors placeholder:text-[#f582ae]/70 focus:border-[#f582ae]",
        className
      )}
      {...props}
    />
  );
}
