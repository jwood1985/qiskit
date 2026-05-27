import { Route, Routes } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { Sidebar } from "./components/Sidebar";
import { GapsDashboard } from "./pages/GapsDashboard";
import { Home } from "./pages/Home";
import { Settings } from "./pages/Settings";

export default function App() {
  return (
    <div className="shell">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <Navbar />
      <div className="shell-body">
        <Sidebar />
        <main id="main" className="main">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/gaps" element={<GapsDashboard />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
