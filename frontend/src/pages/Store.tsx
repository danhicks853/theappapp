/**
 * TheAppApp App Store
 * Browse and install pre-built specialist templates
 */
import { useState, useEffect } from 'react';
import { api, SpecialistTemplate } from '../services/api';

// DiceBear avatar URL generator
const getAvatarUrl = (seed: string) =>
  `https://api.dicebear.com/7.x/avataaars/svg?seed=${seed}`;

export default function Store() {
  const [templates, setTemplates] = useState<SpecialistTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState<SpecialistTemplate | null>(null);
  const [installing, setInstalling] = useState(false);
  const [searchTags, setSearchTags] = useState('');

  useEffect(() => {
    loadTemplates();
  }, [searchTags]);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const data = await api.listStoreSpecialists(searchTags);
      setTemplates(data);
    } catch (error) {
      console.error('Error loading templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleInstall = async (templateId: string) => {
    try {
      setInstalling(true);
      await api.installSpecialist(templateId);
      alert('Specialist installed successfully! Check "Installed Specialists" to see your new team member.');
      setSelectedTemplate(null);
    } catch (error) {
      console.error('Error installing specialist:', error);
      alert('Failed to install specialist. Please try again.');
    } finally {
      setInstalling(false);
    }
  };

  const allTags = Array.from(
    new Set(templates.flatMap(t => t.tags))
  ).sort();

  return (
    <div className="min-h-screen bg-slate-950 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            🏪 TheAppApp App Store
          </h1>
          <p className="text-xl text-slate-300">
            Browse and install pre-built specialists for your team
          </p>
        </div>

        {/* Filter Tags */}
        <div className="mb-6 flex flex-wrap gap-2">
          <button
            onClick={() => setSearchTags('')}
            className={`px-4 py-2 rounded-lg ${
              searchTags === ''
                ? 'bg-navy-600 text-white shadow-lg'
                : 'bg-navy-800 border border-navy-700 text-slate-300 hover:bg-navy-700'
            }`}
          >
            All
          </button>
          {allTags.map(tag => (
            <button
              key={tag}
              onClick={() => setSearchTags(tag)}
              className={`px-4 py-2 rounded-lg ${
                searchTags === tag
                  ? 'bg-navy-600 text-white shadow-lg'
                  : 'bg-navy-800 border border-navy-700 text-slate-300 hover:bg-navy-700'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-navy-500 mx-auto"></div>
            <p className="mt-4 text-slate-300">Loading specialists...</p>
          </div>
        )}

        {/* Templates Grid */}
        {!loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templates.map(template => (
              <div
                key={template.template_id}
                className="bg-navy-900 border border-navy-800 rounded-lg shadow-lg p-6 hover:shadow-navy-600/20 hover:border-navy-700 transition-all cursor-pointer"
                onClick={() => setSelectedTemplate(template)}
              >
                {/* Avatar */}
                <div className="flex justify-center mb-4">
                  <img
                    src={getAvatarUrl(template.avatar_seed)}
                    alt={template.display_name}
                    className="w-24 h-24 rounded-full"
                  />
                </div>

                {/* Name & Role */}
                <h3 className="text-xl font-bold text-center text-white">
                  {template.display_name}
                </h3>
                <p className="text-navy-400 text-center font-medium mb-2">
                  {template.name}
                </p>
                <p className="text-sm text-slate-400 text-center mb-4">
                  v{template.current_version} • by {template.author}
                </p>

                {/* Bio */}
                <p className="text-slate-300 text-sm italic mb-4 line-clamp-3">
                  "{template.bio}"
                </p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1 mb-4">
                  {template.tags.slice(0, 3).map(tag => (
                    <span
                      key={tag}
                      className="px-2 py-1 bg-navy-800 text-slate-300 text-xs rounded border border-navy-700"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                {/* Install Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleInstall(template.template_id);
                  }}
                  disabled={installing}
                  className="w-full bg-navy-600 text-white py-2 rounded-lg hover:bg-navy-500 disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg hover:shadow-navy-500/30 transition-all"
                >
                  {installing ? 'Installing...' : 'Install TheAppApp App'}
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && templates.length === 0 && (
          <div className="text-center py-12">
            <p className="text-slate-300 text-lg">No specialists found with tag "{searchTags}"</p>
            <button
              onClick={() => setSearchTags('')}
              className="mt-4 text-navy-400 hover:text-navy-300 hover:underline"
            >
              View all specialists
            </button>
          </div>
        )}

        {/* Detail Modal */}
        {selectedTemplate && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
            onClick={() => setSelectedTemplate(null)}
          >
            <div
              className="bg-navy-900 border border-navy-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto p-8"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-start mb-6">
                <img
                  src={getAvatarUrl(selectedTemplate.avatar_seed)}
                  alt={selectedTemplate.display_name}
                  className="w-32 h-32 rounded-full mr-6"
                />
                <div className="flex-1">
                  <h2 className="text-3xl font-bold text-white">
                    {selectedTemplate.display_name}
                  </h2>
                  <p className="text-xl text-navy-400 font-medium">
                    {selectedTemplate.name}
                  </p>
                  <p className="text-slate-400">
                    v{selectedTemplate.current_version} • by {selectedTemplate.author}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedTemplate(null)}
                  className="text-slate-400 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>

              {/* Description */}
              <div className="mb-6">
                <h3 className="font-bold text-white mb-2">Description</h3>
                <p className="text-slate-300">{selectedTemplate.description}</p>
              </div>

              {/* Bio */}
              <div className="mb-6">
                <h3 className="font-bold text-white mb-2">About</h3>
                <p className="text-slate-300 italic">"{selectedTemplate.bio}"</p>
              </div>

              {/* Interests */}
              <div className="mb-6">
                <h3 className="font-bold text-white mb-2">Interests</h3>
                <ul className="list-disc list-inside text-slate-300">
                  {selectedTemplate.interests.map((interest, i) => (
                    <li key={i}>{interest}</li>
                  ))}
                </ul>
              </div>

              {/* Favorite Tool */}
              <div className="mb-6">
                <h3 className="font-bold text-white mb-2">Favorite Tool</h3>
                <p className="text-slate-300">{selectedTemplate.favorite_tool}</p>
              </div>

              {/* Quote */}
              <div className="mb-6 p-4 bg-navy-800 rounded-lg border-l-4 border-navy-500">
                <p className="text-slate-200 italic">"{selectedTemplate.quote}"</p>
              </div>

              {/* Tags */}
              <div className="mb-6">
                <h3 className="font-bold text-white mb-2">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedTemplate.tags.map(tag => (
                    <span
                      key={tag}
                      className="px-3 py-1 bg-navy-700 text-navy-200 rounded-full text-sm border border-navy-600"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Install Button */}
              <button
                onClick={() => handleInstall(selectedTemplate.template_id)}
                disabled={installing}
                className="w-full bg-navy-600 text-white py-3 rounded-lg hover:bg-navy-500 disabled:opacity-50 disabled:cursor-not-allowed font-bold text-lg shadow-lg hover:shadow-navy-500/30 transition-all"
              >
                {installing ? 'Installing...' : 'Install TheAppApp App'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
