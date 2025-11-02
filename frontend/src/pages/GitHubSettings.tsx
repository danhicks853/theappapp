import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Github, CheckCircle, XCircle, Loader2, AlertCircle } from 'lucide-react';

interface GitHubStatus {
  connected: boolean;
  github_username?: string;
  github_user_id?: number;
  token_expiry?: string;
  has_refresh_token?: boolean;
}

export default function GitHubSettings() {
  const [status, setStatus] = useState<GitHubStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
    
    // Check for OAuth success/error in URL params
    const params = new URLSearchParams(window.location.search);
    if (params.get('success') === 'true') {
      setSuccess('GitHub account connected successfully!');
      loadStatus();
      // Clean URL
      window.history.replaceState({}, '', '/settings/github');
    } else if (params.get('error')) {
      setError(`GitHub connection failed: ${params.get('error')}`);
      // Clean URL
      window.history.replaceState({}, '', '/settings/github');
    }
  }, []);

  const loadStatus = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/github/status');
      
      if (!response.ok) {
        throw new Error('Failed to load GitHub status');
      }
      
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load status');
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = () => {
    setConnecting(true);
    setError(null);
    
    // Redirect to OAuth endpoint
    window.location.href = 'http://localhost:8000/api/v1/github/connect';
  };

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect your GitHub account? This will remove all stored credentials.')) {
      return;
    }
    
    setDisconnecting(true);
    setError(null);
    setSuccess(null);
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/github/credentials', {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error('Failed to disconnect GitHub');
      }
      
      setSuccess('GitHub account disconnected successfully');
      await loadStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect');
    } finally {
      setDisconnecting(false);
    }
  };

  const formatTokenExpiry = (expiry?: string) => {
    if (!expiry) return 'Never';
    
    const date = new Date(expiry);
    const now = new Date();
    
    if (date < now) {
      return 'Expired (will auto-refresh)';
    }
    
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span className="ml-2">Loading GitHub settings...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold">GitHub Integration</h1>
        <p className="text-muted-foreground mt-2">
          Connect your GitHub account to enable repository management and automated workflows
        </p>
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
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Github className="w-5 h-5" />
            GitHub Account
          </CardTitle>
          <CardDescription>
            Manage your GitHub connection and permissions
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Connection Status */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-4">
              <div>
                {status?.connected ? (
                  <CheckCircle className="w-8 h-8 text-green-500" />
                ) : (
                  <XCircle className="w-8 h-8 text-gray-400" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">
                    {status?.connected ? 'Connected' : 'Not Connected'}
                  </span>
                  {status?.connected && (
                    <Badge variant="default">Active</Badge>
                  )}
                </div>
                {status?.github_username && (
                  <p className="text-sm text-muted-foreground mt-1">
                    Signed in as <span className="font-mono">{status.github_username}</span>
                  </p>
                )}
              </div>
            </div>
            
            <div>
              {status?.connected ? (
                <Button
                  variant="outline"
                  onClick={handleDisconnect}
                  disabled={disconnecting}
                >
                  {disconnecting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Disconnecting...
                    </>
                  ) : (
                    'Disconnect'
                  )}
                </Button>
              ) : (
                <Button
                  onClick={handleConnect}
                  disabled={connecting}
                >
                  {connecting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Connecting...
                    </>
                  ) : (
                    <>
                      <Github className="w-4 h-4 mr-2" />
                      Connect GitHub
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>

          {/* Account Details */}
          {status?.connected && (
            <div className="space-y-4">
              <h3 className="font-semibold">Account Details</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-muted-foreground">Username</label>
                  <p className="font-mono mt-1">{status.github_username || 'N/A'}</p>
                </div>
                
                <div>
                  <label className="text-sm text-muted-foreground">User ID</label>
                  <p className="font-mono mt-1">{status.github_user_id || 'N/A'}</p>
                </div>
                
                <div>
                  <label className="text-sm text-muted-foreground">Token Expiry</label>
                  <p className="mt-1">{formatTokenExpiry(status.token_expiry)}</p>
                </div>
                
                <div>
                  <label className="text-sm text-muted-foreground">Auto-Refresh</label>
                  <p className="mt-1">
                    {status.has_refresh_token ? (
                      <Badge variant="default">Enabled</Badge>
                    ) : (
                      <Badge variant="secondary">Disabled</Badge>
                    )}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Permissions Info */}
          <div className="space-y-4">
            <h3 className="font-semibold">Required Permissions</h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5" />
                <div>
                  <span className="font-medium">repo</span> - Full control of repositories
                </div>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5" />
                <div>
                  <span className="font-medium">user</span> - Read user profile data
                </div>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5" />
                <div>
                  <span className="font-medium">delete_repo</span> - Delete repositories
                </div>
              </div>
            </div>
          </div>

          {/* Security Notice */}
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>Security:</strong> Your GitHub tokens are encrypted at rest using Fernet symmetric encryption. 
              Tokens are automatically refreshed when expired. You can disconnect at any time to revoke access.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Additional Info */}
      <Card>
        <CardHeader>
          <CardTitle>What can the GitHub Specialist do?</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>Create and manage repositories on your behalf</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>Merge pull requests automatically based on your workflow</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>Delete repositories when cleanup is needed</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary">•</span>
              <span>All operations require your prior authorization through gates</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
