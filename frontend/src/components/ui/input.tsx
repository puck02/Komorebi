import type { InputHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-10 rounded-md border border-[#d8cab8] bg-[#fffaf5] px-3 text-sm text-[#2f2924] outline-none transition-colors placeholder:text-[#9a8b7d] focus:border-[#5e7566]",
        className
      )}
      {...props}
    />
  );
}
