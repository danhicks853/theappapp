/**
 * Project Detail Page
 * View project details, specialists, files, and live activity
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, Project, Specialist } from '../services/api';

interface ProjectActivity {
  id: string;
  timestamp: string;
  type: string;
  message: string;
  actor?: string;
}

interface ProjectFile {
  path: string;
  name: string;
  size: number;
  modified: string;
  type: 'file' | 'directory';
}

const getAvatarUrl = (seed: string) =>
  `https://api.dicebear.com/7.x/avataaars/svg?seed=${seed}`;

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [specialists, setSpecialists] = useState<Specialist[]>([]);
  const [activity, setActivity] = useState<ProjectActivity[]>([]);
  const [files, setFiles] = useState<ProjectFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'team' | 'activity' | 'files'>('team');
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  const loadProjectData = async () => {
    if (!projectId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // Load project details
      const projectData = await api.getProject(projectId);
      setProject(projectData);

      // Load all specialists to get details for assigned ones
      const allSpecialists = await api.listSpecialists();
      const assignedSpecialists = allSpecialists.filter(s =>
        projectData.specialist_ids.includes(s.id)
      );
      setSpecialists(assignedSpecialists);

      // Mock activity data - will be replaced with real API
      setActivity([
        {
          id: '1',
          timestamp: new Date().toISOString(),
          type: 'project_created',
          message: 'Project created',
          actor: 'System'
        },
        {
          id: '2',
          timestamp: new Date().toISOString(),
          type: 'specialist_assigned',
          message: `${assignedSpecialists.length} specialists assigned to project`,
          actor: 'System'
        }
      ]);

      // Mock files data - will be replaced with real API
      setFiles([
        {
          path: '/README.md',
          name: 'README.md',
          size: 1024,
          modified: new Date().toISOString(),
          type: 'file'
        },
        {
          path: '/src',
          name: 'src',
          size: 0,
          modified: new Date().toISOString(),
          type: 'directory'
        }
      ]);
    } catch (error) {
      console.error('Error loading project:', error);
      setError('Failed to load project details');
    } finally {
      setLoading(false);
    }
  };

  const handlePauseProject = async () => {
    if (!project || !projectId) return;
    
    try {
      const newStatus = project.status === 'active' ? 'archived' : 'active';
      await api.updateProject(projectId, { status: newStatus });
      setProject({ ...project, status: newStatus });
      alert(`Project ${newStatus === 'active' ? 'resumed' : 'paused'}!`);
    } catch (error) {
      console.error('Error updating project status:', error);
      alert('Failed to update project status');
    }
  };

  const handleDeleteProject = async () => {
    if (!projectId) return;
    
    const confirmed = confirm(
      'Are you sure you want to delete this project? This action cannot be undone.'
    );
    
    if (!confirmed) return;
    
    try {
      setIsDeleting(true);
      // TODO: Implement delete endpoint
      alert('Delete functionality coming soon!');
      // await api.deleteProject(projectId);
      // navigate('/projects');
    } catch (error) {
      console.error('Error deleting project:', error);
      alert('Failed to delete project');
    } finally {
      setIsDeleting(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '-';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${Math.round(bytes / Math.pow(k, i) * 100) / 100} ${sizes[i]}`;
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400 mx-auto"></div>
            <p className="mt-4 text-blue-200">Loading project...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-6 text-center">
            <p className="text-red-200 text-lg mb-4">{error || 'Project not found'}</p>
            <button
              onClick={() => navigate('/projects')}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
            >
              Back to Projects
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/projects')}
            className="text-blue-300 hover:text-white mb-4 flex items-center"
          >
            ← Back to Projects
          </button>
          
          <div className="flex justify-between items-start">
            <div>
              <div className="flex items-center gap-4 mb-2">
                <h1 className="text-4xl font-bold text-white">
                  {project.name}
                </h1>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    project.status === 'active'
                      ? 'bg-green-100 text-green-700'
                      : project.status === 'completed'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {project.status}
                </span>
              </div>
              <p className="text-xl text-blue-200">{project.description}</p>
            </div>
          </div>
        </div>

        {/* Project Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-lg p-6 border border-slate-700">
            <h3 className="text-sm text-blue-300 mb-2">Created</h3>
            <p className="text-white font-medium">
              {new Date(project.created_at).toLocaleDateString()}
            </p>
          </div>
          
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-lg p-6 border border-slate-700">
            <h3 className="text-sm text-blue-300 mb-2">Last Updated</h3>
            <p className="text-white font-medium">
              {new Date(project.updated_at).toLocaleDateString()}
            </p>
          </div>
          
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-lg p-6 border border-slate-700">
            <h3 className="text-sm text-blue-300 mb-2">Team Size</h3>
            <p className="text-white font-medium">
              {specialists.length} Specialist{specialists.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>

        {/* Tabbed Content */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-lg border border-slate-700">
          {/* Tab Headers */}
          <div className="flex border-b border-slate-700">
            <button
              onClick={() => setActiveTab('team')}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === 'team'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              👥 Team ({specialists.length})
            </button>
            <button
              onClick={() => setActiveTab('activity')}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === 'activity'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              📊 Activity ({activity.length})
            </button>
            <button
              onClick={() => setActiveTab('files')}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === 'files'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              📁 Files ({files.length})
            </button>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {/* Team Tab */}
            {activeTab === 'team' && (
              <div>
                {specialists.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">
                    No specialists assigned to this project
                  </p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {specialists.map((specialist) => (
                      <div
                        key={specialist.id}
                        className="bg-slate-900/50 border border-slate-600 rounded-lg p-6 hover:border-blue-500 transition-colors"
                      >
                        <div className="flex items-start gap-4">
                          <img
                            src={getAvatarUrl(specialist.avatar || specialist.id)}
                            alt={specialist.display_name || specialist.name}
                            className="w-16 h-16 rounded-full border-2 border-blue-400"
                          />
                          <div className="flex-1">
                            <h3 className="text-lg font-bold text-white mb-1">
                              {specialist.display_name || specialist.name}
                            </h3>
                            <p className="text-sm text-blue-300 mb-2">
                              {specialist.name}
                            </p>
                            <p className="text-sm text-slate-400">
                              {specialist.description}
                            </p>
                          </div>
                        </div>
                        
                        {specialist.bio && (
                          <p className="text-sm text-slate-300 mt-4 italic">
                            "{specialist.bio}"
                          </p>
                        )}
                        
                        {specialist.favorite_tool && (
                          <div className="mt-4 text-xs text-slate-400">
                            💡 Favorite Tool: {specialist.favorite_tool}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Activity Tab */}
            {activeTab === 'activity' && (
              <div className="space-y-4">
                {activity.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">
                    No activity yet
                  </p>
                ) : (
                  activity.map((item) => (
                    <div
                      key={item.id}
                      className="bg-slate-900/50 border border-slate-600 rounded-lg p-4 hover:border-blue-500 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-blue-400">
                              {item.type.replace(/_/g, ' ')}
                            </span>
                            {item.actor && (
                              <span className="text-xs text-slate-500">• {item.actor}</span>
                            )}
                          </div>
                          <p className="text-white">{item.message}</p>
                        </div>
                        <span className="text-xs text-slate-500 whitespace-nowrap ml-4">
                          {formatTimestamp(item.timestamp)}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Files Tab */}
            {activeTab === 'files' && (
              <div className="space-y-2">
                {files.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">
                    No files yet
                  </p>
                ) : (
                  files.map((file) => (
                    <div
                      key={file.path}
                      className="bg-slate-900/50 border border-slate-600 rounded-lg p-4 hover:border-blue-500 transition-colors cursor-pointer"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">
                            {file.type === 'directory' ? '📁' : '📄'}
                          </span>
                          <div>
                            <p className="text-white font-medium">{file.name}</p>
                            <p className="text-xs text-slate-500">{file.path}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-slate-400">{formatFileSize(file.size)}</p>
                          <p className="text-xs text-slate-500">
                            {new Date(file.modified).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="mt-8 flex flex-wrap gap-4">
          <button
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-medium shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
            disabled
          >
            Start Task (Coming Soon)
          </button>
          
          <button
            onClick={handlePauseProject}
            className={`px-6 py-3 rounded-lg font-medium shadow-lg transition-colors ${
              project.status === 'active'
                ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                : 'bg-green-600 hover:bg-green-700 text-white'
            }`}
          >
            {project.status === 'active' ? '⏸️ Pause Project' : '▶️ Resume Project'}
          </button>

          <button
            onClick={handleDeleteProject}
            disabled={isDeleting}
            className="bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700 font-medium shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDeleting ? 'Deleting...' : '🗑️ Delete Project'}
          </button>
          
          <button
            className="bg-slate-700 text-white px-6 py-3 rounded-lg hover:bg-slate-600 font-medium ml-auto"
            onClick={() => navigate('/projects')}
          >
            ← Back to Projects
          </button>
        </div>
      </div>
    </div>
  );
}
