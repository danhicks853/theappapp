import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import Store from "./pages/Store";
import Team from "./pages/Team";
import Projects from "./pages/Projects";
import Settings from "./pages/Settings";

function Navigation() {
  const location = useLocation();
  
  const isActive = (path: string) => location.pathname === path;
  
  const linkClass = (path: string) => 
    `flex items-center px-4 py-3 rounded-lg transition-colors ${
      isActive(path)
        ? 'bg-blue-600 text-white'
        : 'text-gray-700 hover:bg-gray-100'
    }`;
  
  return (
    <nav className="w-64 bg-white border-r border-gray-200 min-h-screen p-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">TheAppApp</h1>
        <p className="text-sm text-gray-600">AI Agent Platform</p>
      </div>
      
      <div className="space-y-2">
        <Link to="/" className={linkClass('/')}>
          <span className="mr-2">📊</span>
          Dashboard
        </Link>
        
        <Link to="/store" className={linkClass('/store')}>
          <span className="mr-2">🏪</span>
          TheAppApp App Store
        </Link>
        
        <Link to="/team" className={linkClass('/team')}>
          <span className="mr-2">👥</span>
          <div>
            <div>Installed Specialists</div>
            <div className="text-xs opacity-75">(Meet the Team!)</div>
          </div>
        </Link>
        
        <Link to="/projects" className={linkClass('/projects')}>
          <span className="mr-2">📁</span>
          Projects
        </Link>
        
        <Link to="/settings" className={linkClass('/settings')}>
          <span className="mr-2">⚙️</span>
          Settings
        </Link>
      </div>
    </nav>
  );
}

function Dashboard() {
  return (
    <div className="p-8">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Dashboard</h1>
      <p className="text-xl text-gray-600 mb-8">
        Welcome to TheAppApp! Get started by browsing the store or creating a project.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link
          to="/store"
          className="bg-blue-600 text-white p-8 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <h2 className="text-2xl font-bold mb-2">🏪 Browse Store</h2>
          <p>Install pre-built AI specialists for your projects</p>
        </Link>
        
        <Link
          to="/team"
          className="bg-green-600 text-white p-8 rounded-lg hover:bg-green-700 transition-colors"
        >
          <h2 className="text-2xl font-bold mb-2">👥 Meet the Team</h2>
          <p>Manage your installed specialists</p>
        </Link>
        
        <Link
          to="/projects"
          className="bg-purple-600 text-white p-8 rounded-lg hover:bg-purple-700 transition-colors"
        >
          <h2 className="text-2xl font-bold mb-2">📁 Projects</h2>
          <p>Create and manage AI-powered projects</p>
        </Link>
        
        <Link
          to="/settings"
          className="bg-gray-600 text-white p-8 rounded-lg hover:bg-gray-700 transition-colors"
        >
          <h2 className="text-2xl font-bold mb-2">⚙️ Settings</h2>
          <p>Configure your environment and preferences</p>
        </Link>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="flex">
        <Navigation />
        <div className="flex-1 bg-gray-50">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/store" element={<Store />} />
            <Route path="/team" element={<Team />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
