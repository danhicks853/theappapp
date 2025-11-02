/**
 * Meet the Team
 * Installed Specialists - manage your AI team
 */
import { useState, useEffect } from 'react';
import { api, Specialist, SpecialistTemplate } from '../services/api';

const getAvatarUrl = (seed: string) =>
  `https://api.dicebear.com/7.x/avataaars/svg?seed=${seed}`;

const ACHIEVEMENTS = [
  'Outstanding SQL optimization work!',
  'Shipped 15 features without a single bug!',
  'Best code reviewer of the month!',
  'Zero production incidents this month!',
  'Most helpful team member!',
  'Fastest pull request reviews!',
  'Perfect testing coverage achieved!',
  'Exceptional documentation quality!',
];

export default function Team() {
  const [specialists, setSpecialists] = useState<Specialist[]>([]);
  const [storeTemplates, setStoreTemplates] = useState<SpecialistTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [employeeOfMonth, setEmployeeOfMonth] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [installedSpecs, templates] = await Promise.all([
        api.listSpecialists(),
        api.listStoreSpecialists(),
      ]);
      
      setSpecialists(installedSpecs);
      setStoreTemplates(templates);
      
      // Pick Employee of the Month (random)
      const allOptions = [
        ...installedSpecs.map(s => ({
          type: 'installed',
          name: s.display_name || s.name,
          role: s.name,
          avatar: s.avatar || 'default',
          achievement: ACHIEVEMENTS[Math.floor(Math.random() * ACHIEVEMENTS.length)],
        })),
        ...templates.map(t => ({
          type: 'builtin',
          name: t.display_name,
          role: t.name,
          avatar: t.avatar_seed,
          achievement: ACHIEVEMENTS[Math.floor(Math.random() * ACHIEVEMENTS.length)],
        })),
      ];
      
      if (allOptions.length > 0) {
        setEmployeeOfMonth(allOptions[Math.floor(Math.random() * allOptions.length)]);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to remove ${name}? This cannot be undone.`)) {
      return;
    }
    
    try {
      await api.deleteSpecialist(id);
      alert('Specialist removed successfully');
      loadData();
    } catch (error) {
      console.error('Error removing specialist:', error);
      alert('Failed to remove specialist');
    }
  };

  const handleInstall = async (templateId: string) => {
    try {
      await api.installSpecialist(templateId);
      alert('Specialist installed! They are now part of your team.');
      loadData();
    } catch (error) {
      console.error('Error installing specialist:', error);
      alert('Failed to install specialist');
    }
  };

  // Separate installed specialists (from store vs custom)
  const installedFromStore = specialists.filter(s => s.installed_from_store);
  const customSpecialists = specialists.filter(s => !s.installed_from_store);
  
  // Built-in specialists not yet installed
  const installedTemplateIds = new Set(specialists.map(s => s.template_id).filter(Boolean));
  const availableTemplates = storeTemplates.filter(t => !installedTemplateIds.has(t.template_id));

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-1">
            👥 Installed Specialists
          </h1>
          <p className="text-xl text-gray-600">(Meet the Team!)</p>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading your team...</p>
          </div>
        ) : (
          <>
            {/* Employee of the Month */}
            {employeeOfMonth && (
              <div className="mb-8 bg-gradient-to-r from-yellow-50 to-yellow-100 border-2 border-yellow-400 rounded-lg p-6">
                <div className="flex items-center">
                  <div className="text-5xl mr-4">🏆</div>
                  <div className="flex-1">
                    <h2 className="text-2xl font-bold text-gray-900 mb-1">
                      Employee of the Month
                    </h2>
                    <div className="flex items-center">
                      <img
                        src={getAvatarUrl(employeeOfMonth.avatar)}
                        alt={employeeOfMonth.name}
                        className="w-16 h-16 rounded-full mr-4"
                      />
                      <div>
                        <p className="text-xl font-bold text-gray-900">
                          {employeeOfMonth.name}
                        </p>
                        <p className="text-gray-700">{employeeOfMonth.role}</p>
                        <p className="text-gray-600 italic mt-1">
                          "{employeeOfMonth.achievement}"
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Your Installed Specialists */}
            {specialists.length > 0 && (
              <div className="mb-12">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  Your Specialists ({specialists.length})
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {specialists.map(specialist => (
                    <div
                      key={specialist.id}
                      className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
                    >
                      {/* Avatar */}
                      <div className="flex justify-center mb-4">
                        <img
                          src={getAvatarUrl(specialist.avatar || specialist.id)}
                          alt={specialist.display_name || specialist.name}
                          className="w-24 h-24 rounded-full"
                        />
                      </div>

                      {/* Name & Version */}
                      <h3 className="text-xl font-bold text-center text-gray-900">
                        {specialist.display_name || specialist.name}
                      </h3>
                      <p className="text-blue-600 text-center font-medium mb-2">
                        {specialist.name}
                      </p>
                      {specialist.version && (
                        <p className="text-center text-sm text-gray-500 mb-4">
                          v{specialist.version}
                          {specialist.update_available && (
                            <span className="ml-2 text-orange-600">🔔 Update Available</span>
                          )}
                        </p>
                      )}

                      {/* Bio */}
                      {specialist.bio && (
                        <p className="text-gray-700 text-sm italic mb-4 line-clamp-2">
                          "{specialist.bio}"
                        </p>
                      )}

                      {/* Source */}
                      <p className="text-center text-xs text-gray-500 mb-4">
                        {specialist.installed_from_store ? (
                          <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded">
                            From Store
                          </span>
                        ) : (
                          <span className="bg-green-100 text-green-700 px-2 py-1 rounded">
                            Custom
                          </span>
                        )}
                      </p>

                      {/* Actions */}
                      <div className="space-y-2">
                        {specialist.installed_from_store && specialist.update_available && (
                          <button className="w-full bg-orange-600 text-white py-2 rounded-lg hover:bg-orange-700 font-medium">
                            Update Specialist
                          </button>
                        )}
                        {!specialist.installed_from_store && (
                          <button className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 font-medium">
                            Edit Specialist
                          </button>
                        )}
                        <button
                          onClick={() => handleRemove(specialist.id, specialist.display_name || specialist.name)}
                          className="w-full bg-red-600 text-white py-2 rounded-lg hover:bg-red-700 font-medium"
                        >
                          Remove Specialist
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Built-in Specialists Available to Install */}
            {availableTemplates.length > 0 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  Built-in Specialists ({availableTemplates.length} available)
                </h2>
                <p className="text-gray-600 mb-4">
                  These specialists are ready to join your team. Install them to add their expertise to your projects.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {availableTemplates.map(template => (
                    <div
                      key={template.template_id}
                      className="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex justify-center mb-3">
                        <img
                          src={getAvatarUrl(template.avatar_seed)}
                          alt={template.display_name}
                          className="w-16 h-16 rounded-full"
                        />
                      </div>
                      <h3 className="text-lg font-bold text-center text-gray-900">
                        {template.display_name}
                      </h3>
                      <p className="text-blue-600 text-center text-sm font-medium mb-3">
                        {template.name}
                      </p>
                      <button
                        onClick={() => handleInstall(template.template_id)}
                        className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 font-medium text-sm"
                      >
                        Install
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Empty State */}
            {specialists.length === 0 && availableTemplates.length === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-600 text-lg mb-4">
                  No specialists installed yet!
                </p>
                <a
                  href="/store"
                  className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-medium"
                >
                  Browse TheAppApp App Store
                </a>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
