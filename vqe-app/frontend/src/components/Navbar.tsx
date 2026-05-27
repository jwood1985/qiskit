import { NavLink } from "react-router-dom";

export function Navbar() {
  return (
    <nav className="navbar" aria-label="Primary">
      <NavLink to="/" className="navbar-brand">
        VQE<span className="accent"> · </span>Telemetry
      </NavLink>
      <div className="navbar-links">
        <NavLink to="/" end>
          Home
        </NavLink>
        <NavLink to="/settings">Settings</NavLink>
      </div>
    </nav>
  );
}
