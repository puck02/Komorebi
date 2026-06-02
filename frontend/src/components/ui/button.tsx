import { Slot } from "@radix-ui/react-slot";
import { Button as AnimalButton } from "animal-island-ui";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

type ButtonSize = "default" | "icon" | "sm";
type ButtonVariant = "default" | "ghost" | "outline" | "selected";
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean;
  size?: ButtonSize;
  variant?: ButtonVariant;
};

const nativeSizeClasses: Record<ButtonSize, string> = {
  default: "h-10 px-4",
  icon: "h-10 w-10 px-0",
  sm: "h-8 px-3 text-xs"
};

const nativeVariantClasses: Record<ButtonVariant, string> = {
  default: "bg-[#f582ae] text-[#001858] shadow-[0_8px_20px_rgba(245,130,174,0.22)] hover:bg-[#8bd3dd]",
  ghost: "text-[#001858] hover:bg-[#fef6e4]/50",
  outline: "border border-[#f3d2c1] bg-[#fef6e4] text-[#001858] hover:bg-[#f3d2c1]/45",
  selected: "bg-[#8bd3dd] text-[#001858] hover:bg-[#f3d2c1]"
};

const animalTypeByVariant = {
  default: "primary",
  ghost: "text",
  outline: "default",
  selected: "dashed"
} as const;

const animalSizeBySize = {
  default: "middle",
  icon: "middle",
  sm: "small"
} as const;

export function Button({ asChild = false, className, size, type, variant, ...props }: ButtonProps) {
  const resolvedSize = size ?? "default";
  const resolvedVariant = variant ?? "default";
  const shouldUseNativeButton = asChild || className?.includes("liquid-glass-button");

  if (shouldUseNativeButton) {
    const Component = asChild ? Slot : "button";
    return (
      <Component
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-md text-sm font-semibold transition-colors disabled:pointer-events-none disabled:opacity-55",
          nativeSizeClasses[resolvedSize],
          nativeVariantClasses[resolvedVariant],
          className
        )}
        type={asChild ? undefined : type}
        {...props}
      />
    );
  }

  return (
    <AnimalButton
      className={cn("komorebi-animal-button", resolvedSize === "icon" ? "komorebi-animal-button-icon" : "", className)}
      disabled={props.disabled}
      htmlType={type ?? "button"}
      loading={Boolean(props.disabled && type === "submit")}
      size={animalSizeBySize[resolvedSize]}
      type={animalTypeByVariant[resolvedVariant]}
      {...props}
    />
  );
}
