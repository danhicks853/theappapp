/**
 * API Client for TheAppApp Backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface SpecialistTemplate {
  template_id: string;
  name: string;
  display_name: string;
  avatar_seed: string;
  author: string;
  current_version: string;
  description: string;
  bio: string;
  interests: string[];
  favorite_tool: string;
  quote: string;
  tags: string[];
}

export interface Specialist {
  id: string;
  name: string;
  display_name?: string;
  avatar?: string;
  description: string;
  system_prompt: string;
  scope: string;
  project_id?: string;
  web_search_enabled: boolean;
  web_search_config?: any;
  tools_enabled?: any;
  created_at: string;
  updated_at: string;
  version?: string;
  template_id?: string;
  installed_from_store?: boolean;
  store_latest_version?: string;
  update_available?: boolean;
  bio?: string;
  interests?: string[];
  favorite_tool?: string;
  quote?: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
  specialist_ids: string[];
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  // Store endpoints
  async listStoreSpecialists(tags?: string): Promise<SpecialistTemplate[]> {
    const query = tags ? `?tags=${tags}` : '';
    return this.request<SpecialistTemplate[]>(`/api/v1/store/specialists${query}`);
  }

  async getStoreSpecialist(templateId: string): Promise<SpecialistTemplate> {
    return this.request<SpecialistTemplate>(`/api/v1/store/specialists/${templateId}`);
  }

  async installSpecialist(templateId: string, version?: string): Promise<any> {
    return this.request(`/api/v1/store/specialists/${templateId}/install`, {
      method: 'POST',
      body: JSON.stringify({ version }),
    });
  }

  // Specialist endpoints
  async listSpecialists(): Promise<Specialist[]> {
    return this.request<Specialist[]>('/api/v1/specialists');
  }

  async getSpecialist(id: string): Promise<Specialist> {
    return this.request<Specialist>(`/api/v1/specialists/${id}`);
  }

  async createSpecialist(data: Partial<Specialist>): Promise<Specialist> {
    return this.request<Specialist>('/api/v1/specialists', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSpecialist(id: string, data: Partial<Specialist>): Promise<Specialist> {
    return this.request<Specialist>(`/api/v1/specialists/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSpecialist(id: string): Promise<void> {
    return this.request<void>(`/api/v1/specialists/${id}`, {
      method: 'DELETE',
    });
  }

  async generatePrompt(data: {
    name: string;
    description: string;
    role: string;
    capabilities: string[];
    constraints?: string[];
  }): Promise<{ system_prompt: string }> {
    return this.request('/api/v1/specialists/generate-prompt', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Project endpoints
  async listProjects(status?: string): Promise<Project[]> {
    const query = status ? `?status=${status}` : '';
    return this.request<Project[]>(`/api/v1/projects${query}`);
  }

  async getProject(id: string): Promise<Project> {
    return this.request<Project>(`/api/v1/projects/${id}`);
  }

  async createProject(data: {
    name: string;
    description: string;
    specialist_ids: string[];
  }): Promise<Project> {
    return this.request<Project>('/api/v1/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Task endpoints
  async executeTask(data: {
    goal: string;
    description?: string;
    agent_type: string;
    project_id?: string;
    max_steps?: number;
    acceptance_criteria?: string[];
  }): Promise<{ task_id: string; status: string; message: string }> {
    return this.request('/api/v1/tasks/execute', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getTaskResult(taskId: string): Promise<any> {
    return this.request(`/api/v1/tasks/${taskId}/result`);
  }
}

export const api = new ApiClient();
