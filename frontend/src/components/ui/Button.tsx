import { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "md" | "lg" | "xl";
  children: ReactNode;
}

const VARIANT_CLASSES: Record<string, string> = {
  primary: "bg-brand-600 hover:bg-brand-700 text-white focus-visible:ring-brand-400",
  secondary: "bg-slate-100 hover:bg-slate-200 text-slate-900 focus-visible:ring-slate-400",
  danger: "bg-red-600 hover:bg-red-700 text-white focus-visible:ring-red-400",
  ghost: "bg-transparent hover:bg-slate-100 text-slate-700 focus-visible:ring-slate-400",
};

const SIZE_CLASSES: Record<string, string> = {
  md: "px-4 py-2 text-sm rounded-lg",
  lg: "px-6 py-3 text-base rounded-xl",
  xl: "px-8 py-5 text-xl rounded-2xl",
};

export function Button({ variant = "primary", size = "md", className = "", children, ...rest }: ButtonProps) {
  return (
    <button
      className={`font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-4 ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
