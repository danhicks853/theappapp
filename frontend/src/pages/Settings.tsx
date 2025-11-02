import { useState, useEffect } from "react";

type AutonomyLevel = "low" | "medium" | "high";

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

  useEffect(() => {
    fetch("/api/v1/settings/autonomy")
      .then((r) => r.json())
      .then((data) => {
        if (data.autonomy_level) setAutonomy(data.autonomy_level);
      })
      .catch(() => setError("Failed to load current setting"));
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
    </div>
  );
}
