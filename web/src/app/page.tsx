"use client";

import React, { useState, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import {
  ShieldCheck,
  Building2,
  Users,
  Layers,
  KeyRound,
  LogOut,
  ArrowRight,
  UserCheck,
  PlusCircle,
  Mail,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  Trash2,
  UserPlus,
  X,
  Lock,
  FileText,
  Settings as SettingsIcon,
  CreditCard,
  ExternalLink
} from "lucide-react";

import {
  User,
  Organization,
  Member,
  Application,
  Plan,
  Subscription,
  ApplicationRole,
  ApplicationAssignment,
  MainNavSection,
} from "@/types";

import { Sidebar } from "@/components/dashboard/Sidebar";
import { Topbar } from "@/components/dashboard/Topbar";
import { SetupChecklist } from "@/components/dashboard/SetupChecklist";
import { ExecutiveOverviewView } from "@/components/dashboard/ExecutiveOverviewView";
import { TeamManagementView } from "@/components/dashboard/TeamManagementView";
import { BusinessEntitiesView } from "@/components/dashboard/BusinessEntitiesView";
import { ApplicationCatalogView } from "@/components/dashboard/ApplicationCatalogView";
import { IndividualIdentityView } from "@/components/dashboard/IndividualIdentityView";
import { SubscriptionManagementView } from "@/components/dashboard/SubscriptionManagementView";
import { OrganizationApplicationsView } from "@/components/dashboard/OrganizationApplicationsView";

export default function VexIAMApp() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  // Layout & Navigation State
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeSection, setActiveSection] = useState<MainNavSection>("overview");

  // Auth states
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authFirstName, setAuthFirstName] = useState("");
  const [authLastName, setAuthLastName] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);

  // Organizations
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [orgMembers, setOrgMembers] = useState<Member[]>([]);
  const [newOrgName, setNewOrgName] = useState("");
  const [newOrgReg, setNewOrgReg] = useState("");
  const [createOrgModalOpen, setCreateOrgModalOpen] = useState(false);
  const [creatingOrg, setCreatingOrg] = useState(false);
  const creatingOrgRef = useRef(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("MEMBER");
  const [generatedInviteToken, setGeneratedInviteToken] = useState<string | null>(null);

  // Applications & Subscriptions
  const [applications, setApplications] = useState<Application[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [subscribingPlanId, setSubscribingPlanId] = useState<string | null>(null);

  // Application Assignments (Seats)
  const [assignments, setAssignments] = useState<ApplicationAssignment[]>([]);
  const [assigningApp, setAssigningApp] = useState<{ id: string; name: string } | null>(null);
  const [assignUserId, setAssignUserId] = useState<string>("");
  const [assignRoleId, setAssignRoleId] = useState<string>("");
  const [availableRoles, setAvailableRoles] = useState<ApplicationRole[]>([]);
  const [assignLoading, setAssignLoading] = useState(false);

  // Copied State
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => {
      setCopiedId((current) => (current === id ? null : current));
    }, 2000);
  };

  // Check Local Storage on load
  useEffect(() => {
    const savedToken = localStorage.getItem("vex_token");
    const savedUser = localStorage.getItem("vex_user");
    if (savedToken && savedUser) {
      setToken(savedToken);
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        console.error(e);
      }
    }

    const handleAuthExpired = () => {
      setToken(null);
      setUser(null);
    };
    window.addEventListener("vex_auth_expired", handleAuthExpired);
    return () => window.removeEventListener("vex_auth_expired", handleAuthExpired);
  }, []);

  // Fetch initial profile & data when authenticated
  useEffect(() => {
    if (token) {
      fetchCurrentUser();
      fetchOrganizations();
      fetchApplications();
      fetchPlans();
    }
  }, [token]);

  // Load details whenever selectedOrg changes
  useEffect(() => {
    if (selectedOrg) {
      fetchOrgDetails(selectedOrg.id);
    } else {
      setOrgMembers([]);
      setSubscriptions([]);
      setAssignments([]);
    }
  }, [selectedOrg]);

  const fetchCurrentUser = async () => {
    try {
      const res = await api.get("/auth/me");
      setUser(res.data);
      localStorage.setItem("vex_user", JSON.stringify(res.data));
    } catch (e) {
      console.error(e);
    }
  };

  const fetchOrganizations = async () => {
    try {
      const res = await api.get("/organizations");
      setOrganizations(res.data);
      if (res.data.length > 0) {
        setSelectedOrg((prev) => {
          if (prev && res.data.some((o: Organization) => o.id === prev.id)) {
            return prev;
          }
          return res.data[0];
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchOrgDetails = async (orgId: string) => {
    loadOrgMembers(orgId);
    loadOrgSubscriptions(orgId);
    loadOrgAssignments(orgId);
  };

  const loadOrgAssignments = async (orgId: string) => {
    try {
      const res = await api.get(`/organizations/${orgId}/assignments`);
      setAssignments(res.data);
    } catch (e) {
      console.error(e);
      setAssignments([]);
    }
  };

  const openAssignModal = async (appId: string, appName: string) => {
    setAssigningApp({ id: appId, name: appName });
    if (orgMembers.length > 0) {
      setAssignUserId(orgMembers[0].user_id);
    }
    try {
      const res = await api.get(`/applications/${appId}/roles`);
      setAvailableRoles(res.data);
      if (res.data.length > 0) {
        setAssignRoleId(res.data[0].id);
      } else {
        setAssignRoleId("");
      }
    } catch (e) {
      console.error(e);
      setAvailableRoles([]);
      setAssignRoleId("");
    }
  };

  const handleAssignUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg || !assigningApp || !assignUserId) return;
    setAssignLoading(true);
    try {
      await api.post(`/organizations/${selectedOrg.id}/assignments`, {
        user_id: assignUserId,
        application_id: assigningApp.id,
        role_ids: assignRoleId ? [assignRoleId] : [],
      });
      alert("Member assigned to application seat successfully!");
      setAssigningApp(null);
      loadOrgAssignments(selectedOrg.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to assign application access.");
    } finally {
      setAssignLoading(false);
    }
  };

  const handleRevokeAssignment = async (assignmentId: string, memberLabel: string) => {
    if (!selectedOrg) return;
    if (!confirm(`Revoke application seat from "${memberLabel}"? This will free the subscription seat back to the quota.`)) {
      return;
    }
    try {
      await api.delete(`/organizations/${selectedOrg.id}/assignments/${assignmentId}`);
      loadOrgAssignments(selectedOrg.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to revoke assignment.");
    }
  };

  const loadOrgSubscriptions = async (orgId: string) => {
    try {
      const res = await api.get(`/organizations/${orgId}/subscriptions`);
      setSubscriptions(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleBuySubscription = async (planId: string) => {
    if (!selectedOrg) return;
    setSubscribingPlanId(planId);
    try {
      await api.post("/subscriptions", {
        plan_id: planId,
        owner_type: "ORGANIZATION",
        organization_id: selectedOrg.id,
      });
      alert("Subscription activated successfully!");
      loadOrgSubscriptions(selectedOrg.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to activate subscription");
    } finally {
      setSubscribingPlanId(null);
    }
  };

  const fetchPlans = async () => {
    try {
      const res = await api.get("/plans");
      setPlans(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchApplications = async () => {
    try {
      const res = await api.get("/applications");
      setApplications(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const loadOrgMembers = async (orgId: string) => {
    try {
      const res = await api.get(`/organizations/${orgId}/members`);
      setOrgMembers(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    setAuthLoading(true);

    try {
      if (isLoginMode) {
        const res = await api.post("/auth/login", {
          email: authEmail,
          password: authPassword,
        });
        localStorage.setItem("vex_token", res.data.access_token);
        localStorage.setItem("vex_user", JSON.stringify(res.data.user));
        setToken(res.data.access_token);
        setUser(res.data.user);
      } else {
        await api.post("/auth/register", {
          email: authEmail,
          password: authPassword,
          first_name: authFirstName,
          last_name: authLastName,
        });
        const res = await api.post("/auth/login", {
          email: authEmail,
          password: authPassword,
        });
        localStorage.setItem("vex_token", res.data.access_token);
        localStorage.setItem("vex_user", JSON.stringify(res.data.user));
        setToken(res.data.access_token);
        setUser(res.data.user);
      }
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || "Authentication request failed");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("vex_token");
    localStorage.removeItem("vex_user");
    setToken(null);
    setUser(null);
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (creatingOrgRef.current || !newOrgName.trim()) return;
    creatingOrgRef.current = true;
    setCreatingOrg(true);
    try {
      const res = await api.post("/organizations", {
        name: newOrgName.trim(),
        registration_number: newOrgReg || undefined,
      });
      setNewOrgName("");
      setNewOrgReg("");
      setCreateOrgModalOpen(false);
      fetchOrganizations();
      setSelectedOrg(res.data);
      loadOrgMembers(res.data.id);
      setActiveSection("org_members");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create organization");
    } finally {
      creatingOrgRef.current = false;
      setCreatingOrg(false);
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg || !inviteEmail) return;
    try {
      const res = await api.post(`/organizations/${selectedOrg.id}/invitations`, {
        email: inviteEmail,
        role: inviteRole,
      });
      setGeneratedInviteToken(res.data.invitation_token);
      setInviteEmail("");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to send invitation");
    }
  };

  // 1. Unauthenticated Login Screen
  if (!token || !user) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4">
        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500"></div>

          <div className="flex items-center space-x-3 mb-6">
            <div className="h-10 w-10 bg-indigo-600 rounded-xl flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30">
              V
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">VEX IAM</h1>
              <p className="text-xs text-slate-400">Enterprise Identity & Organization Workspace</p>
            </div>
          </div>

          <div className="flex border-b border-slate-800 mb-6">
            <button
              onClick={() => {
                setIsLoginMode(true);
                setAuthError("");
              }}
              className={`flex-1 pb-3 text-sm font-semibold transition-colors ${
                isLoginMode ? "border-b-2 border-indigo-500 text-indigo-400" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => {
                setIsLoginMode(false);
                setAuthError("");
              }}
              className={`flex-1 pb-3 text-sm font-semibold transition-colors ${
                !isLoginMode ? "border-b-2 border-indigo-500 text-indigo-400" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Register Account
            </button>
          </div>

          {authError && (
            <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center text-sm text-rose-400">
              <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
              <span>{authError}</span>
            </div>
          )}

          <form onSubmit={handleAuth} className="space-y-4">
            {!isLoginMode && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">First Name</label>
                  <input
                    type="text"
                    required
                    value={authFirstName}
                    onChange={(e) => setAuthFirstName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                    placeholder="Alex"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Last Name</label>
                  <input
                    type="text"
                    required
                    value={authLastName}
                    onChange={(e) => setAuthLastName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                    placeholder="Smith"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Global VEX Email</label>
              <input
                type="email"
                required
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="name@company.com"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Password</label>
              <input
                type="password"
                required
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={authLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium py-2.5 rounded-xl text-sm transition flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/30"
            >
              <span>{authLoading ? "Authenticating..." : isLoginMode ? "Sign In" : "Create Business Account"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    );
  }

  // 2. Authenticated Admin Dashboard Layout
  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Persistent Left Sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        activeSection={activeSection}
        onSelectSection={(sec) => setActiveSection(sec)}
        organizations={organizations}
        selectedOrg={selectedOrg}
        onSelectOrg={(org) => setSelectedOrg(org)}
        onOpenCreateOrg={() => setCreateOrgModalOpen(true)}
      />

      {/* Main Screen Layout */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Compact Top Navigation Bar */}
        <Topbar
          user={user}
          activeSection={activeSection}
          selectedOrg={selectedOrg}
          onLogout={handleLogout}
          onNavigateSection={(sec) => setActiveSection(sec)}
        />

        {/* Workspace Scrollable Canvas */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6">
          {/* Setup Checklist (Contextual & Dismissible) */}
          <SetupChecklist
            hasOrg={organizations.length > 0}
            hasSubscription={subscriptions.length > 0}
            hasMembers={orgMembers.length > 0}
            onNavigateSection={(sec) => setActiveSection(sec)}
          />

          {/* SECTION 1: Overview */}
          {activeSection === "overview" && (
            <ExecutiveOverviewView
              selectedOrg={selectedOrg}
              members={orgMembers}
              subscriptions={subscriptions}
              applications={applications}
              onNavigateSection={(sec) => setActiveSection(sec)}
              onOpenCreateOrg={() => setCreateOrgModalOpen(true)}
            />
          )}

          {/* SECTION 2: Individual Identity */}
          {activeSection === "identity" && (
            <IndividualIdentityView
              user={user}
              organizations={organizations}
              copiedId={copiedId}
              onCopy={copyToClipboard}
              onResendVerification={async () => {
                try {
                  await api.post("/auth/resend-verification", { email: user.email });
                  alert("Verification email dispatched!");
                } catch (e: any) {
                  alert(e.response?.data?.detail || "Could not resend email");
                }
              }}
            />
          )}

          {/* SECTION 3: Business Entities Directory */}
          {activeSection === "business_entities" && (
            <BusinessEntitiesView
              organizations={organizations}
              selectedOrg={selectedOrg}
              onSelectOrg={(org) => setSelectedOrg(org)}
              copiedId={copiedId}
              onCopy={copyToClipboard}
              onOpenCreateOrg={() => setCreateOrgModalOpen(true)}
              onNavigateToSection={(sec) => setActiveSection(sec)}
              members={orgMembers}
              onDeleteOrg={async (org) => {
                try {
                  await api.delete(`/organizations/${org.id}`);
                  const remaining = organizations.filter((o) => o.id !== org.id);
                  setOrganizations(remaining);
                  if (selectedOrg?.id === org.id) {
                    setSelectedOrg(remaining[0] ?? null);
                  }
                } catch (e: any) {
                  alert(e.response?.data?.detail || "Could not delete business entity");
                }
              }}
            />
          )}

          {/* SECTION 4: Organization Members */}
          {activeSection === "org_members" && (
            <TeamManagementView
              members={orgMembers}
              selectedOrg={selectedOrg}
              copiedId={copiedId}
              onCopy={copyToClipboard}
              inviteEmail={inviteEmail}
              setInviteEmail={setInviteEmail}
              inviteRole={inviteRole}
              setInviteRole={setInviteRole}
              onSendInvite={handleInvite}
              generatedInviteToken={generatedInviteToken}
            />
          )}

          {/* SECTION 5: Application Catalog */}
          {activeSection === "app_catalog" && (
            <ApplicationCatalogView applications={applications} />
          )}

          {/* SECTION 6: Subscriptions & Entitlements */}
          {activeSection === "subscriptions" && (
            <div className="space-y-6">
              {/* Contextual Subscribed Applications with Open Console Buttons */}
              <OrganizationApplicationsView
                selectedOrg={selectedOrg}
                applications={applications}
                subscriptions={subscriptions}
                assignments={assignments}
                members={orgMembers}
                onOpenAssignModal={openAssignModal}
                onRevokeAssignment={handleRevokeAssignment}
                onNavigateToCatalog={() => setActiveSection("app_catalog")}
              />

              {/* Subscriptions & Commercial Plans Quota */}
              <SubscriptionManagementView
                subscriptions={subscriptions}
                plans={plans}
                applications={applications}
                assignments={assignments}
                subscribingPlanId={subscribingPlanId}
                onBuySubscription={handleBuySubscription}
                onOpenAssignModal={openAssignModal}
                onRevokeAssignment={handleRevokeAssignment}
              />
            </div>
          )}

          {/* SECTION 7: Security & Access (Administration) */}
          {activeSection === "security" && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Lock className="w-5 h-5 text-indigo-400" />
                <span>Security Policies & Key Management</span>
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                VEX IAM central authority issues Ed25519 elliptic-curve cryptographic tokens for workstation POS offline activation and OAuth 2.1 OIDC authentication across all ecosystem apps.
              </p>
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs text-slate-300 space-y-2">
                <div className="flex justify-between">
                  <span>Asymmetric Signing Algorithm:</span>
                  <span className="font-mono text-indigo-400 font-bold">Ed25519 (RFC 8032)</span>
                </div>
                <div className="flex justify-between">
                  <span>Offline License Validity Window:</span>
                  <span className="font-mono text-emerald-400 font-bold">30 Days Autonomous</span>
                </div>
                <div className="flex justify-between">
                  <span>Token Issuer:</span>
                  <span className="font-mono text-slate-400">https://iam.vexxero.com</span>
                </div>
              </div>
            </div>
          )}

          {/* SECTION 8: Audit Logs (Administration) */}
          {activeSection === "audit" && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-indigo-400" />
                <span>Audit & Security Ledger</span>
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Immutable audit ledger recording organization role grants, application seat assignments, and token generation events across tenants.
              </p>
              <div className="p-8 bg-slate-950 rounded-xl border border-slate-800 text-center text-xs text-slate-500">
                Audit ledger live stream active. Security events are immutably signed and verified.
              </div>
            </div>
          )}

          {/* SECTION 9: Settings */}
          {activeSection === "settings" && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <SettingsIcon className="w-5 h-5 text-indigo-400" />
                <span>Platform Settings & Workspace Metadata</span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="font-bold text-white mb-1">Organization ID</div>
                  <div className="font-mono text-slate-400 break-all">{selectedOrg?.id || "None selected"}</div>
                </div>
                <div className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="font-bold text-white mb-1">Registered Entity Name</div>
                  <div className="text-slate-300">{selectedOrg?.name || "None"}</div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Create Organization Modal */}
      {createOrgModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Building2 className="w-4 h-4 text-indigo-400" />
                <span>Establish New Business Entity</span>
              </h3>
              <button
                onClick={() => setCreateOrgModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateOrg} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Business Name *</label>
                <input
                  type="text"
                  required
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  placeholder="e.g. B & B Cafe"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Registration Number</label>
                <input
                  type="text"
                  value={newOrgReg}
                  onChange={(e) => setNewOrgReg(e.target.value)}
                  placeholder="e.g. REG-987654"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCreateOrgModalOpen(false)}
                  className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold py-2.5 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newOrgName.trim() || creatingOrg}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:cursor-not-allowed text-white text-xs font-semibold py-2.5 rounded-xl transition shadow-sm shadow-indigo-600/30"
                >
                  {creatingOrg ? "Establishing..." : "Establish Entity"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assign User Seat Modal */}
      {assigningApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-indigo-400" />
                <span>Assign Seat: {assigningApp.name}</span>
              </h3>
              <button
                onClick={() => setAssigningApp(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAssignUser} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Select Member from User Pool</label>
                <select
                  value={assignUserId}
                  onChange={(e) => setAssignUserId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  required
                >
                  {orgMembers.map((m) => {
                    const name = m.user?.profile
                      ? `${m.user.profile.first_name} ${m.user.profile.last_name}`
                      : m.user?.email || m.user_id;
                    return (
                      <option key={m.id} value={m.user_id}>
                        {name} ({m.user?.email}) — [{m.role}]
                      </option>
                    );
                  })}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Application Role</label>
                {availableRoles.length > 0 ? (
                  <select
                    value={assignRoleId}
                    onChange={(e) => setAssignRoleId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {availableRoles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} ({r.code})
                      </option>
                    ))}
                  </select>
                ) : (
                  <p className="text-xs text-slate-400 italic bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                    No application-specific roles configured. Default workspace permissions apply.
                  </p>
                )}
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setAssigningApp(null)}
                  className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold py-2.5 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={assignLoading || !assignUserId}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white text-xs font-semibold py-2.5 rounded-xl transition shadow-sm shadow-indigo-600/30"
                >
                  {assignLoading ? "Assigning..." : "Confirm Seat"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
