import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

const buttonVariants = cva(
  "inline-flex h-10 items-center justify-center gap-2 rounded-md px-4 text-sm font-semibold transition-colors disabled:pointer-events-none disabled:opacity-55",
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
        default: "bg-[#f582ae] text-[#001858] shadow-[0_8px_20px_rgba(245,130,174,0.22)] hover:bg-[#8bd3dd]",
        ghost: "text-[#001858] hover:bg-[#fef6e4]/50",
        outline: "border border-[#f3d2c1] bg-[#fef6e4] text-[#001858] hover:bg-[#f3d2c1]/45",
        selected: "bg-[#8bd3dd] text-[#001858] hover:bg-[#f3d2c1]"
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
