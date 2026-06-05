import type { InputHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-10 rounded-[8px] border border-[#dcc7b6] bg-[#fffdf8] px-3 text-sm font-medium text-[#332319] outline-none transition-[background,border-color,box-shadow] placeholder:text-[#8d6a56]/70 focus:border-[#b86f5b] focus:shadow-[0_0_0_3px_rgba(184,111,91,0.16)]",
        className
      )}
      {...props}
    />
  );
}
