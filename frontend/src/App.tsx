import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Settings from "./pages/Settings";

function App() {
  return (
    <BrowserRouter>
      <nav className="bg-gray-800 text-white p-4">
        <Link to="/settings" className="mr-4">Settings</Link>
      </nav>
      <Routes>
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
