import { useState, useEffect } from "react";

type AutonomyLevel = "low" | "medium" | "high";
type ApiKeyStatus = "not_configured" | "connected" | "invalid" | "testing";

interface AutonomyOption {
  value: AutonomyLevel;
  label: string;
  description: string;
}

const autonomyOptions: AutonomyOption[] = [
  {
    value: "low",
    label: "Low",
    description: "Orchestrator escalates all decisions to humans for review.",
  },
  {
    value: "medium",
    label: "Medium",
    description: "Orchestrator escalates when confidence is below 70%.",
  },
  {
    value: "high",
    label: "High",
    description: "Orchestrator escalates only on very low confidence (<30%).",
  },
];

export default function Settings() {
  const [autonomy, setAutonomy] = useState<AutonomyLevel>("medium");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // API Key state
  const [apiKey, setApiKey] = useState("");
  const [showApiKey, setShowApiKey] = useState(false);
  const [apiKeyStatus, setApiKeyStatus] = useState<ApiKeyStatus>("not_configured");
  const [apiKeySaving, setApiKeySaving] = useState(false);
  const [apiKeyError, setApiKeyError] = useState<string | null>(null);

  // Agent Configuration state
  const [agentConfigs, setAgentConfigs] = useState<Record<string, {model: string, temperature: number, max_tokens: number}>>({});
  const [agentConfigsSaving, setAgentConfigsSaving] = useState(false);
  const [agentConfigsError, setAgentConfigsError] = useState<string | null>(null);

  useEffect(() => {
    // Load autonomy setting
    fetch("/api/v1/settings/autonomy")
      .then((r) => r.json())
      .then((data) => {
        if (data.autonomy_level) setAutonomy(data.autonomy_level);
      })
      .catch(() => setError("Failed to load current setting"));

    // Load API key status
    fetch("/api/v1/settings/api-keys/openai")
      .then((r) => r.json())
      .then((data) => {
        if (data.is_configured) {
          setApiKeyStatus(data.is_active ? "connected" : "invalid");
          setApiKey("••••••••••••••••"); // Masked
        } else {
          setApiKeyStatus("not_configured");
        }
      })
      .catch(() => setApiKeyStatus("not_configured"));

    // Load agent configurations
    fetch("/api/v1/settings/agent-configs")
      .then((r) => r.json())
      .then((data) => {
        const configs: Record<string, {model: string, temperature: number, max_tokens: number}> = {};
        data.forEach((config: any) => {
          configs[config.agent_type] = {
            model: config.model,
            temperature: config.temperature,
            max_tokens: config.max_tokens
          };
        });
        setAgentConfigs(configs);
      })
      .catch(() => setAgentConfigsError("Failed to load agent configurations"));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const resp = await fetch("/api/v1/settings/autonomy", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ autonomy_level: autonomy }),
      });
      if (!resp.ok) throw new Error("Save failed");
    } catch {
      setError("Failed to save autonomy level");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveApiKey = async () => {
    if (!apiKey || apiKey.startsWith("••••")) {
      setApiKeyError("Please enter a valid API key");
      return;
    }

    setApiKeySaving(true);
    setApiKeyError(null);
    try {
      const resp = await fetch("/api/v1/settings/api-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ service: "openai", api_key: apiKey }),
      });
      if (!resp.ok) throw new Error("Save failed");
      setApiKeyStatus("connected");
      setApiKey("••••••••••••••••"); // Mask after saving
      setShowApiKey(false);
    } catch {
      setApiKeyError("Failed to save API key");
    } finally {
      setApiKeySaving(false);
    }
  };

  const handleTestApiKey = async () => {
    setApiKeyStatus("testing");
    setApiKeyError(null);
    try {
      const resp = await fetch("/api/v1/settings/api-keys/openai/test");
      const data = await resp.json();
      setApiKeyStatus(data.is_valid ? "connected" : "invalid");
      if (!data.is_valid) {
        setApiKeyError("API key is invalid or expired");
      }
    } catch {
      setApiKeyStatus("invalid");
      setApiKeyError("Failed to test API key");
    }
  };

  const handleSaveAgentConfigs = async () => {
    setAgentConfigsSaving(true);
    setAgentConfigsError(null);
    try {
      const configsArray = Object.entries(agentConfigs).map(([agent_type, config]) => ({
        agent_type,
        ...config
      }));
      const resp = await fetch("/api/v1/settings/agent-configs", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(configsArray),
      });
      if (!resp.ok) throw new Error("Save failed");
    } catch {
      setAgentConfigsError("Failed to save agent configurations");
    } finally {
      setAgentConfigsSaving(false);
    }
  };

  const applyPreset = (preset: "cost" | "quality" | "balanced") => {
    const presets = {
      cost: { model: "gpt-4o-mini", temperature: 0.7 },
      quality: { model: "gpt-4o", temperature: 0.7 },
      balanced: { model: "gpt-4o-mini", temperature: 0.7 }
    };
    const config = presets[preset];
    const updated = { ...agentConfigs };
    Object.keys(updated).forEach(agent => {
      updated[agent] = { ...updated[agent], model: config.model, temperature: config.temperature };
    });
    setAgentConfigs(updated);
  };

  const updateAgentConfig = (agentType: string, field: string, value: any) => {
    setAgentConfigs(prev => ({
      ...prev,
      [agentType]: { ...prev[agentType], [field]: value }
    }));
  };

  const currentIndex = autonomyOptions.findIndex((opt) => opt.value === autonomy);

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-4">Orchestrator Autonomy</h2>
        <p className="text-sm text-gray-600 mb-4">
          Choose how much autonomy the orchestrator has when making decisions.
        </p>

        <div className="flex items-center gap-4 mb-4">
          <span className="text-sm font-medium">Low</span>
          <input
            type="range"
            min="0"
            max="2"
            value={currentIndex}
            onChange={(e) => setAutonomy(autonomyOptions[Number(e.target.value)].value)}
            className="flex-1"
          />
          <span className="text-sm font-medium">High</span>
        </div>

        <div className="bg-gray-50 rounded p-4 mb-4">
          <h3 className="font-medium text-sm mb-1">
            {autonomyOptions[currentIndex].label} Autonomy
          </h3>
          <p className="text-xs text-gray-600">
            {autonomyOptions[currentIndex].description}
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>

        {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
      </section>

      {/* API Keys Section */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-4">API Keys</h2>
        <p className="text-sm text-gray-600 mb-4">
          Configure your OpenAI API key for LLM operations.
        </p>

        <div className="bg-gray-50 rounded p-4 mb-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="font-medium text-sm">OpenAI API Key</h3>
              <p className="text-xs text-gray-500">Required for all agent operations</p>
            </div>
            <div className="flex items-center gap-2">
              {apiKeyStatus === "connected" && (
                <span className="text-xs text-green-600 font-medium flex items-center gap-1">
                  <span className="w-2 h-2 bg-green-600 rounded-full"></span>
                  Connected
                </span>
              )}
              {apiKeyStatus === "invalid" && (
                <span className="text-xs text-red-600 font-medium flex items-center gap-1">
                  <span className="w-2 h-2 bg-red-600 rounded-full"></span>
                  Invalid
                </span>
              )}
              {apiKeyStatus === "testing" && (
                <span className="text-xs text-blue-600 font-medium">Testing...</span>
              )}
              {apiKeyStatus === "not_configured" && (
                <span className="text-xs text-yellow-600 font-medium flex items-center gap-1">
                  <span className="w-2 h-2 bg-yellow-600 rounded-full"></span>
                  Not Configured
                </span>
              )}
            </div>
          </div>

          <div className="flex gap-2 mb-2">
            <input
              type={showApiKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className="flex-1 px-3 py-2 border rounded text-sm"
            />
            <button
              onClick={() => setShowApiKey(!showApiKey)}
              className="px-3 py-2 border rounded text-sm hover:bg-gray-100"
            >
              {showApiKey ? "Hide" : "Show"}
            </button>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleSaveApiKey}
              disabled={apiKeySaving}
              className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
            >
              {apiKeySaving ? "Saving..." : "Save Key"}
            </button>
            {apiKeyStatus !== "not_configured" && (
              <button
                onClick={handleTestApiKey}
                disabled={apiKeyStatus === "testing"}
                className="bg-gray-200 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-300 disabled:opacity-50"
              >
                {apiKeyStatus === "testing" ? "Testing..." : "Test Connection"}
              </button>
            )}
          </div>

          {apiKeyError && (
            <p className="text-red-600 text-xs mt-2">{apiKeyError}</p>
          )}
        </div>

        <p className="text-xs text-gray-500">
          Your API key is encrypted and stored securely. Never share your API key with others.
        </p>
      </section>

      {/* Agent Configuration Section */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-4">Agent Model Configuration</h2>
        <p className="text-sm text-gray-600 mb-4">
          Configure LLM model and parameters for each agent type.
        </p>

        {/* Preset Buttons */}
        <div className="flex gap-2 mb-6">
          <button onClick={() => applyPreset("cost")} className="px-3 py-2 border rounded text-sm hover:bg-gray-50">
            Cost Optimized (All gpt-4o-mini)
          </button>
          <button onClick={() => applyPreset("quality")} className="px-3 py-2 border rounded text-sm hover:bg-gray-50">
            Quality (All gpt-4o)
          </button>
          <button onClick={() => applyPreset("balanced")} className="px-3 py-2 border rounded text-sm hover:bg-gray-50">
            Balanced
          </button>
        </div>

        {/* Agent Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {Object.entries(agentConfigs).map(([agentType, config]) => (
            <div key={agentType} className="bg-gray-50 rounded p-4">
              <h3 className="font-medium text-sm mb-3 capitalize">{agentType.replace(/_/g, " ")}</h3>
              
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-600 block mb-1">Model</label>
                  <select
                    value={config.model}
                    onChange={(e) => updateAgentConfig(agentType, "model", e.target.value)}
                    className="w-full px-2 py-1 border rounded text-sm"
                  >
                    <option value="gpt-4o-mini">gpt-4o-mini</option>
                    <option value="gpt-4o">gpt-4o</option>
                    <option value="gpt-4-turbo">gpt-4-turbo</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-gray-600 block mb-1">
                    Temperature: {config.temperature.toFixed(1)}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={config.temperature}
                    onChange={(e) => updateAgentConfig(agentType, "temperature", parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="text-xs text-gray-600 block mb-1">Max Tokens</label>
                  <input
                    type="number"
                    min="1000"
                    max="16000"
                    step="1000"
                    value={config.max_tokens}
                    onChange={(e) => updateAgentConfig(agentType, "max_tokens", parseInt(e.target.value))}
                    className="w-full px-2 py-1 border rounded text-sm"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={handleSaveAgentConfigs}
          disabled={agentConfigsSaving}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {agentConfigsSaving ? "Saving..." : "Save All Configurations"}
        </button>

        {agentConfigsError && (
          <p className="text-red-600 text-sm mt-2">{agentConfigsError}</p>
        )}
      </section>
    </div>
  );
}
