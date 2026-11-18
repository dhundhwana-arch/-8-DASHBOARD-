import React from "react";
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  FlaskConical,
  PlugZap,
} from "lucide-react";
import { IntegrationSourceStatus } from "../api/dashboard";
import { useI18n } from "../i18n/I18nProvider";

interface ProvenanceBadgeProps {
  status: IntegrationSourceStatus;
  compact?: boolean;
}

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({
  status,
  compact = false,
}) => {
  const { t } = useI18n();

  const config: Record<
    IntegrationSourceStatus,
    { label: string; classes: string; Icon: React.ComponentType<{ className?: string }> }
  > = {
    VERIFIED: {
      label: t.statusVerified,
      classes: "bg-emerald-50 text-emerald-800 border-emerald-200",
      Icon: CheckCircle2,
    },
    MOCK_DEV: {
      label: t.statusMockDev,
      classes: "bg-amber-50 text-amber-900 border-amber-300",
      Icon: FlaskConical,
    },
    CONTRACT_UNCONFIGURED: {
      label: t.statusContractUnconfigured,
      classes: "bg-slate-100 text-slate-700 border-slate-300",
      Icon: PlugZap,
    },
    UNAVAILABLE: {
      label: t.statusUnavailable,
      classes: "bg-red-50 text-red-800 border-red-200",
      Icon: AlertOctagon,
    },
    CONTRACT_MISMATCH: {
      label: t.statusContractMismatch,
      classes: "bg-rose-50 text-rose-800 border-rose-300",
      Icon: AlertTriangle,
    },
  };

  const { label, classes, Icon } = config[status];

  return (
    <span
      data-provenance-status={status}
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${
        compact ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs"
      } ${classes}`}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
};
