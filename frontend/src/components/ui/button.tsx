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
        default: "bg-[#6d6875] text-[#fff8f4] hover:bg-[#b5838d]",
        ghost: "text-[#6d6875] hover:bg-[#ffcdb2]/50",
        outline: "border border-[#ffb4a2] bg-[#fff3ed] text-[#6d6875] hover:bg-[#ffcdb2]/45",
        selected: "bg-[#b5838d] text-[#fff8f4] hover:bg-[#6d6875]"
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
