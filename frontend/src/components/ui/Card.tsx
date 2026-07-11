import clsx from "clsx";
import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export function Card({ children, className, hover, onClick }: CardProps) {
  return (
    <div
      className={clsx(
        "ethara-card animate-fade-in",
        hover &&
          "hover:border-ethara-primary/40 transition-colors duration-200 cursor-pointer",
        className,
      )}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={clsx("mb-4", className)}>{children}</div>;
}

export function CardTitle({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <h3 className={clsx("text-lg font-semibold text-white", className)}>
      {children}
    </h3>
  );
}
