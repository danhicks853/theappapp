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
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            🏪 TheAppApp App Store
          </h1>
          <p className="text-xl text-gray-600">
            Browse and install pre-built specialists for your team
          </p>
        </div>

        {/* Filter Tags */}
        <div className="mb-6 flex flex-wrap gap-2">
          <button
            onClick={() => setSearchTags('')}
            className={`px-4 py-2 rounded-lg ${
              searchTags === ''
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
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
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading specialists...</p>
          </div>
        )}

        {/* Templates Grid */}
        {!loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {templates.map(template => (
              <div
                key={template.template_id}
                className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow cursor-pointer"
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
                <h3 className="text-xl font-bold text-center text-gray-900">
                  {template.display_name}
                </h3>
                <p className="text-blue-600 text-center font-medium mb-2">
                  {template.name}
                </p>
                <p className="text-sm text-gray-500 text-center mb-4">
                  v{template.current_version} • by {template.author}
                </p>

                {/* Bio */}
                <p className="text-gray-700 text-sm italic mb-4 line-clamp-3">
                  "{template.bio}"
                </p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1 mb-4">
                  {template.tags.slice(0, 3).map(tag => (
                    <span
                      key={tag}
                      className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded"
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
                  className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
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
            <p className="text-gray-600 text-lg">No specialists found with tag "{searchTags}"</p>
            <button
              onClick={() => setSearchTags('')}
              className="mt-4 text-blue-600 hover:underline"
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
              className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto p-8"
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
                  <h2 className="text-3xl font-bold text-gray-900">
                    {selectedTemplate.display_name}
                  </h2>
                  <p className="text-xl text-blue-600 font-medium">
                    {selectedTemplate.name}
                  </p>
                  <p className="text-gray-500">
                    v{selectedTemplate.current_version} • by {selectedTemplate.author}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedTemplate(null)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  ×
                </button>
              </div>

              {/* Description */}
              <div className="mb-6">
                <h3 className="font-bold text-gray-900 mb-2">Description</h3>
                <p className="text-gray-700">{selectedTemplate.description}</p>
              </div>

              {/* Bio */}
              <div className="mb-6">
                <h3 className="font-bold text-gray-900 mb-2">About</h3>
                <p className="text-gray-700 italic">"{selectedTemplate.bio}"</p>
              </div>

              {/* Interests */}
              <div className="mb-6">
                <h3 className="font-bold text-gray-900 mb-2">Interests</h3>
                <ul className="list-disc list-inside text-gray-700">
                  {selectedTemplate.interests.map((interest, i) => (
                    <li key={i}>{interest}</li>
                  ))}
                </ul>
              </div>

              {/* Favorite Tool */}
              <div className="mb-6">
                <h3 className="font-bold text-gray-900 mb-2">Favorite Tool</h3>
                <p className="text-gray-700">{selectedTemplate.favorite_tool}</p>
              </div>

              {/* Quote */}
              <div className="mb-6 p-4 bg-gray-50 rounded-lg border-l-4 border-blue-600">
                <p className="text-gray-700 italic">"{selectedTemplate.quote}"</p>
              </div>

              {/* Tags */}
              <div className="mb-6">
                <h3 className="font-bold text-gray-900 mb-2">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedTemplate.tags.map(tag => (
                    <span
                      key={tag}
                      className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
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
                className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-bold text-lg"
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
