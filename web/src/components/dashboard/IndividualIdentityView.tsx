"use client";

import React from "react";
import {
  ShieldCheck,
  KeyRound,
  CheckCircle2,
  Mail,
  Copy,
  Check,
  Building2,
  ExternalLink
} from "lucide-react";
import { User, Organization } from "@/types";

interface IndividualIdentityViewProps {
  user: User;
  organizations: Organization[];
  copiedId: string | null;
  onCopy: (text: string, id: string) => void;
  onResendVerification: () => void;
}

export function IndividualIdentityView({
  user,
  organizations,
  copiedId,
  onCopy,
  onResendVerification,
}: IndividualIdentityViewProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-indigo-400" />
            <span>Global Individual Identity Profile</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Root identity subject recognized across the entire Vexxero federated platform.
          </p>
        </div>
      </div>

      {/* Identity Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <p className="text-xs text-slate-400 mb-1">Subject Identifier (UUID)</p>
          <div className="flex items-center justify-between font-mono text-xs text-indigo-300 break-all bg-slate-950 p-2.5 rounded-xl border border-slate-800">
            <span>{user.id}</span>
            <button
              type="button"
              onClick={() => onCopy(user.id, "user-id")}
              className="text-slate-400 hover:text-white ml-2 shrink-0"
            >
              {copiedId === "user-id" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <p className="text-xs text-slate-400 mb-1">Account Global Status</p>
          <div className="mt-2">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5"></span>
              {user.status}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Active subject allowed to participate in workspace organizations.</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
          <p className="text-xs text-slate-400 mb-1">Primary Email Verification</p>
          <div className="mt-2 flex items-center justify-between">
            {user.email_verified ? (
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                Verified
              </span>
            ) : (
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  Unverified
                </span>
                <button
                  onClick={onResendVerification}
                  className="text-xs text-indigo-400 hover:text-indigo-300 underline font-semibold"
                >
                  Resend Email
                </button>
              </div>
            )}
          </div>
          <p className="text-[11px] text-slate-500 mt-2 truncate">{user.email}</p>
        </div>
      </div>

      {/* Organization Memberships */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
        <h3 className="text-sm font-bold text-white mb-1">Workspace Organization Memberships</h3>
        <p className="text-xs text-slate-400 mb-4">
          Business entities where your personal identity has established workspace authorization.
        </p>

        {organizations.length === 0 ? (
          <p className="text-xs text-slate-500 italic">No organization memberships established.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {organizations.map((org) => (
              <div
                key={org.id}
                className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex items-center justify-between"
              >
                <div>
                  <h4 className="font-bold text-sm text-white">{org.name}</h4>
                  <p className="text-xs text-slate-400 font-mono">
                    {org.registration_number ? `Reg: ${org.registration_number}` : org.id}
                  </p>
                </div>
                <span className="text-xs bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2.5 py-1 rounded-full font-semibold">
                  {org.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
