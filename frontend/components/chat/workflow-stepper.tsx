'use client';

import { Check, MessageSquare, FileText, RefreshCw, CheckCircle2 } from 'lucide-react';

export type ConvStatus = 'active' | 'draft_ready' | 'confirmed';

interface WorkflowStepperProps {
  status: ConvStatus;
  className?: string;
}

const steps = [
  { label: '讨论', icon: MessageSquare },
  { label: '生成草稿', icon: FileText },
  { label: '审阅修改', icon: RefreshCw },
  { label: '已确认', icon: CheckCircle2 },
];

function getActiveStep(status: ConvStatus): number {
  switch (status) {
    case 'active':
      return 0;
    case 'draft_ready':
      return 2;
    case 'confirmed':
      return 3;
  }
}

export function WorkflowStepper({ status, className = '' }: WorkflowStepperProps) {
  const activeStep = getActiveStep(status);

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {steps.map((step, idx) => {
        const isCompleted = idx < activeStep;
        const isActive = idx === activeStep;

        return (
          <div key={step.label} className="flex items-center">
            {idx > 0 && (
              <div
                className={`h-px w-4 ${
                  idx <= activeStep ? 'bg-primary' : 'bg-border'
                }`}
              />
            )}
            <div className="flex items-center gap-1">
              <div
                className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-medium ${
                  isCompleted
                    ? 'bg-primary text-primary-foreground'
                    : isActive
                      ? 'bg-primary/20 text-primary ring-1 ring-primary'
                      : 'bg-muted text-muted-foreground'
                }`}
              >
                {isCompleted ? <Check className="h-3 w-3" /> : idx + 1}
              </div>
              <span
                className={`text-xs whitespace-nowrap ${
                  isActive
                    ? 'text-primary font-medium'
                    : isCompleted
                      ? 'text-foreground'
                      : 'text-muted-foreground'
                }`}
              >
                {step.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
