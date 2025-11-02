import React, { useState, useEffect } from 'react';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { AlertCircle, Save, RotateCcw, CheckCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface Permission {
  agent_type: string;
  tool_name: string;
  operation: string;
  allowed: boolean;
}

interface PermissionMatrix {
  [agentType: string]: {
    [toolName: string]: Set<string>; // Set of allowed operations
  };
}

const AGENT_TYPES = [
  'backend_dev',
  'frontend_dev',
  'workshopper',
  'security_expert',
  'devops_engineer',
  'qa_engineer',
  'github_specialist',
  'orchestrator'
];

const TOOLS = [
  { name: 'container', operations: ['create', 'destroy', 'execute', 'list'] },
  { name: 'file_system', operations: ['read', 'write', 'delete', 'list'] },
  { name: 'web_search', operations: ['search'] },
  { name: 'code_validator', operations: ['validate'] },
  { name: 'github', operations: ['create_repo', 'delete_repo', 'merge_pr', 'list_repos'] },
  { name: 'database', operations: ['read', 'write'] },
];

const TEMPLATES = {
  restrictive: 'Restrictive (Read-only)',
  balanced: 'Balanced (Default)',
  permissive: 'Permissive (All access)',
  custom: 'Custom'
};

export default function ToolPermissions() {
  const [matrix, setMatrix] = useState<PermissionMatrix>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [template, setTemplate] = useState<string>('custom');
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [pendingChanges, setPendingChanges] = useState<any>(null);

  useEffect(() => {
    loadPermissions();
  }, []);

  const loadPermissions = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Load permissions for each agent type
      const matrixData: PermissionMatrix = {};
      
      for (const agentType of AGENT_TYPES) {
        const response = await fetch(`http://localhost:8001/api/v1/tools/permissions/${agentType}`);
        
        if (!response.ok) {
          throw new Error(`Failed to load permissions for ${agentType}`);
        }
        
        const data = await response.json();
        
        matrixData[agentType] = {};
        
        data.permissions.forEach((perm: any) => {
          if (!matrixData[agentType][perm.tool_name]) {
            matrixData[agentType][perm.tool_name] = new Set();
          }
          
          perm.operations.forEach((op: string) => {
            matrixData[agentType][perm.tool_name].add(op);
          });
        });
      }
      
      setMatrix(matrixData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load permissions');
    } finally {
      setLoading(false);
    }
  };

  const togglePermission = (agentType: string, toolName: string, operation: string) => {
    setMatrix(prev => {
      const newMatrix = JSON.parse(JSON.stringify(
        Object.fromEntries(
          Object.entries(prev).map(([key, value]) => [
            key,
            Object.fromEntries(
              Object.entries(value).map(([k, v]) => [k, Array.from(v as Set<string>)])
            )
          ])
        )
      ));
      
      if (!newMatrix[agentType]) {
        newMatrix[agentType] = {};
      }
      if (!newMatrix[agentType][toolName]) {
        newMatrix[agentType][toolName] = [];
      }
      
      const operations = newMatrix[agentType][toolName];
      const index = operations.indexOf(operation);
      
      if (index > -1) {
        operations.splice(index, 1);
      } else {
        operations.push(operation);
      }
      
      // Convert back to Sets
      const result: PermissionMatrix = {};
      for (const [agent, tools] of Object.entries(newMatrix)) {
        result[agent] = {};
        for (const [tool, ops] of Object.entries(tools as any)) {
          result[agent][tool] = new Set(ops as string[]);
        }
      }
      
      setHasChanges(true);
      return result;
    });
  };

  const isDangerousChange = (updates: any[]): boolean => {
    // Check if removing critical orchestrator permissions
    return updates.some(update => 
      update.agent_type === 'orchestrator' && 
      update.allowed === false &&
      ['container', 'file_system', 'database'].includes(update.tool_name)
    );
  };

  const savePermissions = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);
    
    try {
      // Build updates array
      const updates: any[] = [];
      
      for (const [agentType, tools] of Object.entries(matrix)) {
        for (const [toolName, operations] of Object.entries(tools)) {
          for (const operation of operations) {
            updates.push({
              agent_type: agentType,
              tool_name: toolName,
              operation,
              allowed: true
            });
          }
        }
      }
      
      // Check for dangerous changes
      if (isDangerousChange(updates)) {
        setPendingChanges({ updates });
        setShowConfirmDialog(true);
        setSaving(false);
        return;
      }
      
      await performSave({ updates });
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save permissions');
      setSaving(false);
    }
  };

  const performSave = async (payload: any) => {
    const response = await fetch('http://localhost:8001/api/v1/tools/permissions', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
      throw new Error('Failed to save permissions');
    }
    
    setSuccess(true);
    setHasChanges(false);
    setSaving(false);
    setShowConfirmDialog(false);
    setPendingChanges(null);
    
    // Hide success message after 3 seconds
    setTimeout(() => setSuccess(false), 3000);
  };

  const resetToDefaults = async () => {
    if (confirm('Are you sure you want to reset all permissions to defaults? This cannot be undone.')) {
      await loadPermissions();
      setHasChanges(false);
    }
  };

  const applyTemplate = (templateName: string) => {
    setTemplate(templateName);
    
    if (templateName === 'custom') return;
    
    const newMatrix: PermissionMatrix = {};
    
    for (const agentType of AGENT_TYPES) {
      newMatrix[agentType] = {};
      
      for (const tool of TOOLS) {
        newMatrix[agentType][tool.name] = new Set();
        
        if (templateName === 'permissive') {
          // Grant all operations
          tool.operations.forEach(op => {
            newMatrix[agentType][tool.name].add(op);
          });
        } else if (templateName === 'restrictive') {
          // Grant only read/list operations
          tool.operations.forEach(op => {
            if (op === 'read' || op === 'list' || op === 'search') {
              newMatrix[agentType][tool.name].add(op);
            }
          });
        } else if (templateName === 'balanced') {
          // Load defaults (current state)
          loadPermissions();
          return;
        }
      }
    }
    
    setMatrix(newMatrix);
    setHasChanges(true);
  };

  const isPermissionAllowed = (agentType: string, toolName: string, operation: string): boolean => {
    return matrix[agentType]?.[toolName]?.has(operation) || false;
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading permissions...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Tool Permissions</h1>
          <p className="text-muted-foreground mt-2">
            Configure which tools each agent type can access
          </p>
        </div>
        
        <div className="flex gap-2">
          <Select value={template} onValueChange={applyTemplate}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select template" />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(TEMPLATES).map(([key, label]) => (
                <SelectItem key={key} value={key}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Button
            variant="outline"
            onClick={resetToDefaults}
            disabled={saving}
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset to Defaults
          </Button>
          
          <Button
            onClick={savePermissions}
            disabled={!hasChanges || saving}
          >
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert>
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>Permissions saved successfully!</AlertDescription>
        </Alert>
      )}

      {showConfirmDialog && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-bold">Warning: Dangerous changes detected!</p>
              <p>You are removing critical permissions from the orchestrator. This may prevent the system from functioning correctly.</p>
              <div className="flex gap-2 mt-4">
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => performSave(pendingChanges)}
                >
                  Continue Anyway
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setShowConfirmDialog(false);
                    setPendingChanges(null);
                    setSaving(false);
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </AlertDescription>
        </Alert>
      )}

      <div className="border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[150px] sticky left-0 bg-background">
                  Agent Type
                </TableHead>
                {TOOLS.map(tool => (
                  <TableHead key={tool.name} className="text-center" colSpan={tool.operations.length}>
                    {tool.name}
                  </TableHead>
                ))}
              </TableRow>
              <TableRow>
                <TableHead className="w-[150px] sticky left-0 bg-background"></TableHead>
                {TOOLS.map(tool =>
                  tool.operations.map(op => (
                    <TableHead key={`${tool.name}-${op}`} className="text-center text-xs">
                      {op}
                    </TableHead>
                  ))
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {AGENT_TYPES.map(agentType => (
                <TableRow key={agentType}>
                  <TableCell className="font-medium sticky left-0 bg-background">
                    {agentType}
                  </TableCell>
                  {TOOLS.map(tool =>
                    tool.operations.map(op => (
                      <TableCell key={`${agentType}-${tool.name}-${op}`} className="text-center">
                        <div className="flex justify-center">
                          <Checkbox
                            checked={isPermissionAllowed(agentType, tool.name, op)}
                            onCheckedChange={() => togglePermission(agentType, tool.name, op)}
                          />
                        </div>
                      </TableCell>
                    ))
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {hasChanges && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            You have unsaved changes. Click "Save Changes" to apply them.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
