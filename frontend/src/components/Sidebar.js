import { Link, useLocation } from "react-router-dom";
import { Button } from "./ui/button";
import Logo from "./Logo";
import {
  LayoutDashboard,
  Settings,
  LogOut,
  Zap,
  Github,
  CreditCard,
  Code2,
  Cloud,
  Import,
  Loader2,
  User,
} from "lucide-react";

export default function Sidebar({
  user,
  logout,
  creditsRemaining,
  creditsPercentage,
  onUpgrade,
  onConnectGitHub,
  onImportGitHub,
  githubLoading,
}) {
  const location = useLocation();

  const navItems = [
    { path: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { path: "/settings", icon: Settings, label: "Settings" },
  ];

  if (user?.is_admin) {
    navItems.push({ path: "/admin", icon: Code2, label: "Admin" });
  }

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-64 bg-deep border-r border-white/5 flex flex-col z-40"
      data-testid="sidebar"
    >
      {/* Logo */}
      <div className="p-6 border-b border-white/5">
        <Link to="/dashboard" className="flex items-center gap-3 overflow-hidden">
          <Logo size="small" />
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              data-testid={`nav-${item.label.toLowerCase()}`}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-electric/10 text-electric"
                  : "text-white/60 hover:text-white hover:bg-white/5"
              }`}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}

        {/* GitHub section */}
        <div className="pt-4 mt-4 border-t border-white/5">
          <p className="text-xs text-white/30 px-3 mb-2 uppercase tracking-wider">
            GitHub
          </p>
          {user?.github_username ? (
            <>
              <div className="flex items-center gap-2 px-3 py-2 text-sm text-white/60">
                <Github className="w-4 h-4" />
                <span className="truncate">{user.github_username}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start text-white/60 hover:text-white"
                onClick={onImportGitHub}
                disabled={githubLoading}
                data-testid="import-github-btn"
              >
                {githubLoading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Import className="w-4 h-4 mr-2" />
                )}
                Import Repository
              </Button>
            </>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start text-white/60 hover:text-white"
              onClick={onConnectGitHub}
              data-testid="connect-github-btn"
            >
              <Github className="w-4 h-4 mr-2" />
              Connect GitHub
            </Button>
          )}
        </div>
      </nav>

      {/* Credits + User */}
      <div className="p-4 border-t border-white/5 space-y-4">
        {/* Credits */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-white/50 flex items-center gap-1">
              <Zap className="w-3 h-3" /> Credits
            </span>
            <span className="text-electric font-medium">
              {creditsRemaining} remaining
            </span>
          </div>
          <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full bg-electric rounded-full transition-all"
              style={{ width: `${Math.max(creditsPercentage, 2)}%` }}
            />
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full text-xs text-white/40 hover:text-electric"
            onClick={onUpgrade}
            data-testid="upgrade-plan-btn"
          >
            <CreditCard className="w-3 h-3 mr-1" />
            Upgrade Plan
          </Button>
        </div>

        {/* User */}
        <div className="flex items-center gap-3 p-2 rounded-lg bg-white/5">
          <div className="w-8 h-8 rounded-full bg-electric/20 flex items-center justify-center">
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt=""
                className="w-8 h-8 rounded-full"
              />
            ) : (
              <User className="w-4 h-4 text-electric" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white truncate">{user?.name}</p>
            <p className="text-xs text-white/40 truncate">{user?.email}</p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="text-white/40 hover:text-red-400 p-1"
            onClick={logout}
            data-testid="logout-btn"
          >
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </aside>
  );
}
