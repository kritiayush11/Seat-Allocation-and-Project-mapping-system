import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Building2,
  Armchair,
  Bot,
  X,
} from "lucide-react";
import clsx from "clsx";

const links = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/employees", icon: Users, label: "Employees" },
  { to: "/seats", icon: Armchair, label: "Seats" },
  { to: "/projects", icon: Building2, label: "Projects" },
  { to: "/ai", icon: Bot, label: "AI Assistant" },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={clsx(
          "fixed top-0 left-0 h-full w-64 z-40 flex flex-col",
          "bg-ethara-card border-r border-ethara-border",
          "transition-transform duration-300 ease-in-out",
          open ? "translate-x-0" : "-translate-x-full",
          "lg:translate-x-0 lg:static lg:z-auto",
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-ethara-border">
          <div className="flex items-center gap-2.5 select-none">
            <img
              src="/favicon.svg"
              alt="Ethara icon"
              className="h-8 w-8 object-contain shrink-0"
            />
            <img
              src="/logo.png"
              alt="Ethara.Ai"
              className="h-6 object-contain"
            />
          </div>
          <button
            onClick={onClose}
            className="lg:hidden text-ethara-muted hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {links.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={onClose}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                  isActive
                    ? "bg-ethara-primary/10 text-ethara-primary border border-ethara-primary/20"
                    : "text-ethara-muted hover:text-white hover:bg-ethara-hover",
                )
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-ethara-border">
          <p className="text-xs text-ethara-muted">Ethara.AI © 2024</p>
          <p className="text-xs text-ethara-muted/50 mt-0.5">v1.0.0</p>
        </div>
      </aside>
    </>
  );
}
