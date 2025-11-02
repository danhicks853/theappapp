/**
 * Projects
 * Create and manage projects with assigned specialists
 */
import { useState, useEffect } from 'react';
import { api, Project, Specialist } from '../services/api';

const getAvatarUrl = (seed: string) =>
  `https://api.dicebear.com/7.x/avataaars/svg?seed=${seed}`;

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [specialists, setSpecialists] = useState<Specialist[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);

  // Form state
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [selectedSpecialistIds, setSelectedSpecialistIds] = useState<string[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [projectsData, specialistsData] = await Promise.all([
        api.listProjects(),
        api.listSpecialists(),
      ]);
      setProjects(projectsData);
      setSpecialists(specialistsData);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!projectName.trim()) {
      alert('Please enter a project name');
      return;
    }
    if (selectedSpecialistIds.length === 0) {
      alert('Please select at least one specialist');
      return;
    }

    try {
      setCreating(true);
      await api.createProject({
        name: projectName,
        description: projectDescription,
        specialist_ids: selectedSpecialistIds,
      });
      
      alert('Project created successfully!');
      setShowCreateModal(false);
      setProjectName('');
      setProjectDescription('');
      setSelectedSpecialistIds([]);
      loadData();
    } catch (error) {
      console.error('Error creating project:', error);
      alert('Failed to create project');
    } finally {
      setCreating(false);
    }
  };

  const toggleSpecialist = (id: string) => {
    setSelectedSpecialistIds(prev =>
      prev.includes(id)
        ? prev.filter(sid => sid !== id)
        : [...prev, id]
    );
  };

  const getSpecialistsByIds = (ids: string[]) => {
    return specialists.filter(s => ids.includes(s.id));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">
              📁 Projects
            </h1>
            <p className="text-xl text-blue-200">
              Manage your AI-powered projects
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-medium shadow-lg"
          >
            + New Project
          </button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400 mx-auto"></div>
            <p className="mt-4 text-blue-200">Loading projects...</p>
          </div>
        )}

        {/* Projects Grid */}
        {!loading && projects.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map(project => {
              const projectSpecialists = getSpecialistsByIds(project.specialist_ids || []);
              return (
                <div
                  key={project.id}
                  className="bg-slate-800/50 backdrop-blur-sm rounded-lg shadow-md p-6 hover:shadow-xl hover:bg-slate-800/70 transition-all border border-slate-700"
                >
                  {/* Status Badge */}
                  <div className="flex justify-between items-start mb-4">
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

                  {/* Project Name */}
                  <h3 className="text-xl font-bold text-white mb-2">
                    {project.name}
                  </h3>

                  {/* Description */}
                  <p className="text-blue-200 text-sm mb-4 line-clamp-2">
                    {project.description}
                  </p>

                  {/* Specialists */}
                  <div className="mb-4">
                    <p className="text-xs text-blue-300 mb-2">Team:</p>
                    <div className="flex -space-x-2">
                      {projectSpecialists.slice(0, 5).map(specialist => (
                        <img
                          key={specialist.id}
                          src={getAvatarUrl(specialist.avatar || specialist.id)}
                          alt={specialist.display_name || specialist.name}
                          title={specialist.display_name || specialist.name}
                          className="w-8 h-8 rounded-full border-2 border-white"
                        />
                      ))}
                      {projectSpecialists.length > 5 && (
                        <div className="w-8 h-8 rounded-full border-2 border-white bg-gray-200 flex items-center justify-center text-xs text-gray-600">
                          +{projectSpecialists.length - 5}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* View Button */}
                  <button className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 font-medium shadow-md">
                    View Project
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Empty State */}
        {!loading && projects.length === 0 && (
          <div className="text-center py-12 bg-slate-800/30 rounded-lg border border-slate-700">
            <p className="text-blue-200 text-lg mb-4">
              No projects yet. Create your first project to get started!
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-medium shadow-lg"
            >
              + Create First Project
            </button>
          </div>
        )}

        {/* Create Project Modal */}
        {showCreateModal && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
            onClick={() => setShowCreateModal(false)}
          >
            <div
              className="bg-slate-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto p-8 border border-slate-700"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-3xl font-bold text-white">
                    Create New Project
                  </h2>
                  <p className="text-blue-200">
                    Assign specialists to work on this project
                  </p>
                </div>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="text-blue-300 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>

              {/* Form */}
              <div className="space-y-6">
                {/* Project Name */}
                <div>
                  <label className="block text-sm font-medium text-blue-200 mb-2">
                    Project Name *
                  </label>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="Customer Portal Redesign"
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {/* Project Description */}
                <div>
                  <label className="block text-sm font-medium text-blue-200 mb-2">
                    Description
                  </label>
                  <textarea
                    value={projectDescription}
                    onChange={(e) => setProjectDescription(e.target.value)}
                    placeholder="Rebuild the customer portal with modern UI/UX and improved performance..."
                    rows={4}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {/* Select Specialists */}
                <div>
                  <label className="block text-sm font-medium text-blue-200 mb-2">
                    Select Specialists * ({selectedSpecialistIds.length} selected)
                  </label>
                  {specialists.length === 0 ? (
                    <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-4">
                      <p className="text-yellow-200">
                        No specialists available. Install specialists from TheAppApp App Store first.
                      </p>
                      <a
                        href="/store"
                        className="text-blue-400 hover:underline mt-2 inline-block"
                      >
                        Browse Store →
                      </a>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto">
                      {specialists.map(specialist => (
                        <div
                          key={specialist.id}
                          onClick={() => toggleSpecialist(specialist.id)}
                          className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                            selectedSpecialistIds.includes(specialist.id)
                              ? 'border-blue-500 bg-blue-900/30'
                              : 'border-slate-600 bg-slate-700/50 hover:border-slate-500'
                          }`}
                        >
                          <div className="flex items-center">
                            <img
                              src={getAvatarUrl(specialist.avatar || specialist.id)}
                              alt={specialist.display_name || specialist.name}
                              className="w-12 h-12 rounded-full mr-3"
                            />
                            <div className="flex-1">
                              <p className="font-bold text-white">
                                {specialist.display_name || specialist.name}
                              </p>
                              <p className="text-sm text-blue-300">
                                {specialist.name}
                              </p>
                            </div>
                            {selectedSpecialistIds.includes(specialist.id) && (
                              <span className="text-blue-400 text-xl">✓</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 mt-8">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 bg-slate-700 text-white py-3 rounded-lg hover:bg-slate-600 font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  disabled={creating || !projectName.trim() || selectedSpecialistIds.length === 0}
                  className="flex-1 bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg"
                >
                  {creating ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
