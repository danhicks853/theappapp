import React, { useState, useEffect } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { 
  ChevronLeft, 
  ChevronRight, 
  Download, 
  Search, 
  X,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';

interface AuditLog {
  id: number;
  timestamp: string;
  agent_id: string;
  agent_type: string;
  tool_name: string;
  operation: string;
  project_id?: string;
  task_id?: string;
  parameters?: any;
  allowed: boolean;
  success?: boolean;
  result?: any;
  error_message?: string;
}

interface Filters {
  agent_id?: string;
  tool_name?: string;
  project_id?: string;
  allowed?: boolean;
}

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [limit] = useState(50);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<Filters>({});
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  
  // Filter inputs
  const [agentIdInput, setAgentIdInput] = useState('');
  const [toolNameInput, setToolNameInput] = useState('');
  const [projectIdInput, setProjectIdInput] = useState('');
  const [allowedFilter, setAllowedFilter] = useState<string>('all');

  useEffect(() => {
    loadLogs();
  }, [filters, page]);

  const loadLogs = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      
      if (filters.agent_id) params.append('agent_id', filters.agent_id);
      if (filters.tool_name) params.append('tool_name', filters.tool_name);
      if (filters.project_id) params.append('project_id', filters.project_id);
      if (filters.allowed !== undefined) params.append('allowed', String(filters.allowed));
      params.append('limit', String(limit));
      
      const response = await fetch(`http://localhost:8001/api/v1/audit/logs?${params}`);
      
      if (!response.ok) {
        throw new Error('Failed to load audit logs');
      }
      
      const data = await response.json();
      
      setLogs(data.logs);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    const newFilters: Filters = {};
    
    if (agentIdInput) newFilters.agent_id = agentIdInput;
    if (toolNameInput) newFilters.tool_name = toolNameInput;
    if (projectIdInput) newFilters.project_id = projectIdInput;
    if (allowedFilter !== 'all') {
      newFilters.allowed = allowedFilter === 'allowed';
    }
    
    setFilters(newFilters);
    setPage(1);
  };

  const clearFilters = () => {
    setAgentIdInput('');
    setToolNameInput('');
    setProjectIdInput('');
    setAllowedFilter('all');
    setFilters({});
    setPage(1);
  };

  const toggleRowExpansion = (id: number) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const exportToCSV = () => {
    // Build CSV content
    const headers = ['ID', 'Timestamp', 'Agent ID', 'Agent Type', 'Tool', 'Operation', 'Project', 'Task', 'Allowed', 'Success', 'Error'];
    const rows = logs.map(log => [
      log.id,
      log.timestamp,
      log.agent_id,
      log.agent_type,
      log.tool_name,
      log.operation,
      log.project_id || '',
      log.task_id || '',
      log.allowed,
      log.success !== undefined ? log.success : '',
      log.error_message || ''
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    // Download
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const hasActiveFilters = Object.keys(filters).length > 0;

  if (loading && logs.length === 0) {
    return (
      <div className="p-6">
        <div className="text-center">Loading audit logs...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Audit Logs</h1>
          <p className="text-muted-foreground mt-2">
            View all tool access attempts and executions
          </p>
        </div>
        
        <Button onClick={exportToCSV} disabled={logs.length === 0}>
          <Download className="w-4 h-4 mr-2" />
          Export to CSV
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Agent ID</label>
              <Input
                placeholder="Filter by agent ID"
                value={agentIdInput}
                onChange={(e) => setAgentIdInput(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Tool Name</label>
              <Input
                placeholder="Filter by tool"
                value={toolNameInput}
                onChange={(e) => setToolNameInput(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Project ID</label>
              <Input
                placeholder="Filter by project"
                value={projectIdInput}
                onChange={(e) => setProjectIdInput(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <Select value={allowedFilter} onValueChange={setAllowedFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="allowed">Allowed</SelectItem>
                  <SelectItem value="denied">Denied</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <div className="flex gap-2 mt-4">
            <Button onClick={applyFilters}>
              <Search className="w-4 h-4 mr-2" />
              Apply Filters
            </Button>
            
            {hasActiveFilters && (
              <Button variant="outline" onClick={clearFilters}>
                <X className="w-4 h-4 mr-2" />
                Clear Filters
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="text-red-600 p-4 border border-red-300 rounded-lg bg-red-50">
          {error}
        </div>
      )}

      {/* Logs Table */}
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]"></TableHead>
              <TableHead>Timestamp</TableHead>
              <TableHead>Agent</TableHead>
              <TableHead>Tool</TableHead>
              <TableHead>Operation</TableHead>
              <TableHead>Project</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Result</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-muted-foreground">
                  No audit logs found
                </TableCell>
              </TableRow>
            ) : (
              logs.map((log) => (
                <React.Fragment key={log.id}>
                  <TableRow className="cursor-pointer hover:bg-muted/50">
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleRowExpansion(log.id)}
                      >
                        {expandedRows.has(log.id) ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </Button>
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatTimestamp(log.timestamp)}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="text-sm font-mono">{log.agent_id}</span>
                        <span className="text-xs text-muted-foreground">{log.agent_type}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{log.tool_name}</Badge>
                    </TableCell>
                    <TableCell>{log.operation}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {log.project_id || '-'}
                    </TableCell>
                    <TableCell>
                      {log.allowed ? (
                        <Badge variant="default" className="bg-green-500">Allowed</Badge>
                      ) : (
                        <Badge variant="destructive">Denied</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {log.success !== undefined && (
                        <Badge variant={log.success ? "default" : "destructive"}>
                          {log.success ? 'Success' : 'Failed'}
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                  
                  {expandedRows.has(log.id) && (
                    <TableRow>
                      <TableCell colSpan={8} className="bg-muted/30">
                        <div className="p-4 space-y-3">
                          {log.task_id && (
                            <div>
                              <span className="font-semibold text-sm">Task ID:</span>
                              <span className="ml-2 text-sm font-mono">{log.task_id}</span>
                            </div>
                          )}
                          
                          {log.parameters && Object.keys(log.parameters).length > 0 && (
                            <div>
                              <span className="font-semibold text-sm">Parameters:</span>
                              <pre className="mt-1 text-xs bg-background p-2 rounded border overflow-x-auto">
                                {JSON.stringify(log.parameters, null, 2)}
                              </pre>
                            </div>
                          )}
                          
                          {log.result && (
                            <div>
                              <span className="font-semibold text-sm">Result:</span>
                              <pre className="mt-1 text-xs bg-background p-2 rounded border overflow-x-auto">
                                {JSON.stringify(log.result, null, 2)}
                              </pre>
                            </div>
                          )}
                          
                          {log.error_message && (
                            <div>
                              <span className="font-semibold text-sm text-red-600">Error:</span>
                              <p className="mt-1 text-sm text-red-600">{log.error_message}</p>
                            </div>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Showing {logs.length} of {total} logs
        </div>
        
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1 || loading}
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Previous
          </Button>
          
          <div className="flex items-center px-3 py-2 text-sm">
            Page {page}
          </div>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(p => p + 1)}
            disabled={logs.length < limit || loading}
          >
            Next
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </div>
    </div>
  );
}
