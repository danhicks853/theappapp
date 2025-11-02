import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Brain, TrendingUp, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface ReasoningStep {
  step: number;
  description: string;
  rationale: string;
}

interface Alternative {
  option: string;
  pros: string[];
  cons: string[];
  rejected_reason: string;
}

interface DecisionData {
  decision: string;
  reasoning_steps: ReasoningStep[];
  confidence_score: number;
  alternatives_considered: Alternative[];
  risk_level: 'low' | 'medium' | 'high';
  estimated_cost?: number;
  estimated_time?: string;
  trade_offs?: {
    speed_vs_quality?: string;
    cost_vs_benefit?: string;
    risk_vs_reward?: string;
  };
}

interface DecisionExplanationProps {
  decision: DecisionData;
  agentId?: string;
  agentType?: string;
}

export default function DecisionExplanation({ decision, agentId, agentType }: DecisionExplanationProps) {
  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'high':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Brain className="w-6 h-6 text-primary" />
              <div>
                <CardTitle>AI Decision Explanation</CardTitle>
                {(agentId || agentType) && (
                  <CardDescription>
                    {agentType && <span className="font-mono">{agentType}</span>}
                    {agentId && agentType && <span> • </span>}
                    {agentId && <span className="text-xs">{agentId}</span>}
                  </CardDescription>
                )}
              </div>
            </div>
            
            <div className={`px-4 py-2 rounded-lg border ${getRiskColor(decision.risk_level)}`}>
              <div className="flex items-center gap-2">
                {decision.risk_level === 'low' && <CheckCircle2 className="w-4 h-4" />}
                {decision.risk_level === 'medium' && <AlertTriangle className="w-4 h-4" />}
                {decision.risk_level === 'high' && <XCircle className="w-4 h-4" />}
                <span className="font-semibold capitalize">{decision.risk_level} Risk</span>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Decision */}
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-2">Decision</h3>
              <p className="text-lg font-medium">{decision.decision}</p>
            </div>

            {/* Confidence Score */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-muted-foreground">Confidence</h3>
                <span className="text-sm font-semibold">{decision.confidence_score}%</span>
              </div>
              <Progress value={decision.confidence_score} className={`h-2 ${getConfidenceColor(decision.confidence_score)}`} />
            </div>

            {/* Estimates */}
            {(decision.estimated_cost || decision.estimated_time) && (
              <div className="flex gap-4">
                {decision.estimated_cost && (
                  <div>
                    <h3 className="text-sm font-semibold text-muted-foreground mb-1">Estimated Cost</h3>
                    <p className="text-sm">${decision.estimated_cost.toFixed(2)}</p>
                  </div>
                )}
                {decision.estimated_time && (
                  <div>
                    <h3 className="text-sm font-semibold text-muted-foreground mb-1">Estimated Time</h3>
                    <p className="text-sm">{decision.estimated_time}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Reasoning Steps */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Reasoning Process</CardTitle>
          <CardDescription>Step-by-step decision logic</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {decision.reasoning_steps.map((step) => (
              <div key={step.step} className="flex gap-4">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
                    {step.step}
                  </div>
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold mb-1">{step.description}</h4>
                  <p className="text-sm text-muted-foreground">{step.rationale}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Alternatives Considered */}
      {decision.alternatives_considered && decision.alternatives_considered.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Alternatives Considered</CardTitle>
            <CardDescription>Other options evaluated before making this decision</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {decision.alternatives_considered.map((alt, index) => (
                <div key={index} className="border rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <h4 className="font-semibold">{alt.option}</h4>
                    <Badge variant="outline">Rejected</Badge>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    <div>
                      <h5 className="text-sm font-semibold text-green-600 mb-2">Pros</h5>
                      <ul className="text-sm space-y-1">
                        {alt.pros.map((pro, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                            <span>{pro}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    
                    <div>
                      <h5 className="text-sm font-semibold text-red-600 mb-2">Cons</h5>
                      <ul className="text-sm space-y-1">
                        {alt.cons.map((con, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <XCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                            <span>{con}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                  
                  <div className="text-sm bg-muted p-3 rounded">
                    <span className="font-semibold">Rejection Reason: </span>
                    <span className="text-muted-foreground">{alt.rejected_reason}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Trade-offs */}
      {decision.trade_offs && Object.keys(decision.trade_offs).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Trade-offs
            </CardTitle>
            <CardDescription>Key considerations in this decision</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {decision.trade_offs.speed_vs_quality && (
                <div className="flex items-start gap-3">
                  <div className="font-semibold text-sm min-w-[140px]">Speed vs Quality:</div>
                  <div className="text-sm text-muted-foreground">{decision.trade_offs.speed_vs_quality}</div>
                </div>
              )}
              {decision.trade_offs.cost_vs_benefit && (
                <div className="flex items-start gap-3">
                  <div className="font-semibold text-sm min-w-[140px]">Cost vs Benefit:</div>
                  <div className="text-sm text-muted-foreground">{decision.trade_offs.cost_vs_benefit}</div>
                </div>
              )}
              {decision.trade_offs.risk_vs_reward && (
                <div className="flex items-start gap-3">
                  <div className="font-semibold text-sm min-w-[140px]">Risk vs Reward:</div>
                  <div className="text-sm text-muted-foreground">{decision.trade_offs.risk_vs_reward}</div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
