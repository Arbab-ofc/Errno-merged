import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { Activity, BriefcaseBusiness, ChartNoAxesCombined, ChevronLeft, CircleHelp, ClipboardList, LayoutDashboard, LogOut, Menu, Shield, Store, Users, Wrench } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

const links = [
  { to: "/admin/dashboard", label: "Overview", icon: LayoutDashboard, permission: "dashboard.read" },
  { to: "/admin/shop-owners", label: "Shop Owners", icon: Store, permission: "users.read" },
  { to: "/admin/workers", label: "Workers", icon: Users, permission: "users.read" },
  { to: "/admin/jobs", label: "Jobs", icon: BriefcaseBusiness, permission: "jobs.read" },
  { to: "/admin/bookings", label: "Bookings", icon: ClipboardList },
  { to: "/admin/categories", label: "Categories", icon: Wrench },
  { to: "/admin/attendance", label: "Attendance", icon: Activity },
  { to: "/admin/ratings", label: "Ratings", icon: ChartNoAxesCombined },
  { to: "/admin/disputes", label: "Reports & disputes", icon: CircleHelp },
  { to: "/admin/notifications", label: "Notifications", icon: Activity },
  { to: "/admin/system-health", label: "System health", icon: Activity },
];

export function AppShell() {
  const { user, admin, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const permissions = new Set(admin?.permissions || []);
  return (
    <div className={"admin-shell " + (collapsed ? "collapsed " : "") + (mobileOpen ? "mobile-open" : "")}>
      <aside className="admin-sidebar">
        <div className="admin-brand"><span className="brand-mark">E</span><span className="brand-copy"><b>ERRNO</b><small>OPERATIONS</small></span></div>
        <div className="workspace-label"><span className="workspace-dot" /> Production workspace</div>
        <nav aria-label="Admin navigation">
          <div className="nav-caption">WORKSPACE</div>
          {links.filter((link) => !link.permission || permissions.has(link.permission)).map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => "admin-nav-link " + (isActive ? "active" : "")} onClick={() => setMobileOpen(false)}>
              <Icon size={17} strokeWidth={1.8} /><span>{label}</span>
            </NavLink>
          ))}
          <div className="nav-caption settings-caption">ACCOUNT</div>
          <NavLink to="/admin/settings" className={({ isActive }) => "admin-nav-link " + (isActive ? "active" : "")} onClick={() => setMobileOpen(false)}>
            <Wrench size={17} strokeWidth={1.8} /><span>Settings</span>
          </NavLink>
        </nav>
        <div className="sidebar-bottom">
          <div className="security-note"><Shield size={15} /><span>Access is verified by ERRNO API</span></div>
          <button className="collapse-button" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}><ChevronLeft size={17} /></button>
        </div>
      </aside>
      <div className="admin-main">
        <header className="admin-topbar">
          <button className="mobile-menu" onClick={() => setMobileOpen((value) => !value)} aria-label="Toggle navigation"><Menu size={20} /></button>
          <div className="crumb"><span>ERRNO</span><b>/</b><strong>Administration</strong></div>
          <div className="topbar-spacer" />
          <div className="admin-identity"><div className="identity-avatar">{user?.photoURL ? <img src={user.photoURL} alt="" /> : (admin?.email || user?.email || "A")[0].toUpperCase()}</div><div><b>{admin?.email || user?.email || "Administrator"}</b><small>Server-authorized admin</small></div></div>
          <button className="logout-button" onClick={() => logout()} aria-label="Sign out"><LogOut size={16} /><span>Sign out</span></button>
        </header>
        <main className="admin-content"><Outlet /></main>
      </div>
      {mobileOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    </div>
  );
}
