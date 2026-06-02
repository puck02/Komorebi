import type { InputHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 rounded-full border-2 border-[#f3d2c1] bg-[#fffdf8] px-4 text-sm font-medium text-[#001858] shadow-[0_3px_0_#f3d2c1] outline-none transition-all placeholder:text-[#f582ae]/65 focus:border-[#8bd3dd] focus:shadow-[0_4px_0_#8bd3dd]",
        className
      )}
      {...props}
    />
  );
}
