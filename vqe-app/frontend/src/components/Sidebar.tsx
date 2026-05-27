import { NavLink } from "react-router-dom";

export function Sidebar() {
  return (
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="sidebar-section">Workspace</div>
      <NavLink to="/" end>
        Home
      </NavLink>
      <NavLink to="/settings">Settings</NavLink>

      <div className="sidebar-section">Observability</div>
      <NavLink to="/gaps">GAPS dashboard</NavLink>
    </aside>
  );
}
