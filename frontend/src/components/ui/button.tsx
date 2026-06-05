import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

const buttonVariants = cva(
  "inline-flex h-10 items-center justify-center gap-2 rounded-[8px] px-4 text-sm font-semibold transition-[background,border-color,box-shadow,color,transform,opacity] duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#b86f5b]/25 disabled:pointer-events-none disabled:opacity-55 active:translate-y-px",
  {
    defaultVariants: {
      size: "default",
      variant: "default"
    },
    variants: {
      size: {
        default: "h-10 px-4",
        icon: "h-10 w-10 px-0",
        sm: "h-8 px-3 text-xs"
      },
      variant: {
        default: "bg-[#b86f5b] text-[#fffdf8] shadow-[0_10px_22px_rgba(184,111,91,0.24)] hover:bg-[#a7604f]",
        ghost: "text-[#332319] hover:bg-[#fffdf8]/75 hover:shadow-[inset_0_0_0_1px_rgba(220,199,182,0.7)]",
        outline: "border border-[#dcc7b6] bg-[#fffaf2] text-[#332319] hover:border-[#c8ad99] hover:bg-[#fffdf8]",
        selected: "border border-[#b86f5b] bg-[#b86f5b] text-[#fffdf8] shadow-[0_8px_18px_rgba(184,111,91,0.2)] hover:bg-[#a7604f]"
      }
    }
  }
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  };

export function Button({ asChild = false, className, size, variant, ...props }: ButtonProps) {
  const Component = asChild ? Slot : "button";
  return <Component className={cn(buttonVariants({ className, size, variant }))} {...props} />;
}
