import { Link } from "react-router-dom";

export function Navbar() {
  return (
    <header className="navbar" role="banner">
      <Link to="/" className="navbar-brand">
        VQE<span className="accent"> · </span>Telemetry
      </Link>
      <span className="navbar-meta">
        Ground-state energy · LiH / H₂
      </span>
    </header>
  );
}
