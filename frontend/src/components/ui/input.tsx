import type { InputHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-10 rounded-md border border-[#ffb4a2] bg-[#fff8f4] px-3 text-sm text-[#6d6875] outline-none transition-colors placeholder:text-[#b5838d]/70 focus:border-[#b5838d]",
        className
      )}
      {...props}
    />
  );
}
