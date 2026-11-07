"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import {
  ShieldCheck,
  Building2,
  Users,
  Layers,
  KeyRound,
  LogOut,
  Laptop,
  ArrowRight,
  UserCheck,
  PlusCircle,
  Mail,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
} from "lucide-react";

interface UserProfile {
  first_name: string;
  last_name: string;
}

interface User {
  id: string;
  email: string;
  status: string;
  email_verified: boolean;
  profile?: UserProfile;
}

interface Organization {
  id: string;
  name: string;
  registration_number?: string;
  status: string;
}

interface Member {
  id: string;
  user_id: string;
  role: string;
  user?: User;
}

interface Application {
  id: string;
  code: string;
  name: string;
  description?: string;
  type: string;
}

interface Plan {
  id: string;
  application_id: string;
  code: string;
  name: string;
  description?: string;
  user_seats: number;
  device_seats: number;
}

interface Subscription {
  id: string;
  plan_id: string;
  owner_type: string;
  organization_id?: string;
  status: string;
  expires_at?: string;
  created_at: string;
  plan?: Plan;
}

interface Device {
  id: string;
  organization_id: string;
  name: string;
  fingerprint: string;
  status: string;
  created_at: string;
}

export default function VexIAMApp() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<"individual" | "organizations" | "apps">(
    "individual"
  );

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
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("MEMBER");
  const [generatedInviteToken, setGeneratedInviteToken] = useState<string | null>(null);

  // Applications
  const [applications, setApplications] = useState<Application[]>([]);
  const [newAppCode, setNewAppCode] = useState("");
  const [newAppName, setNewAppName] = useState("");
  const [newAppType, setNewAppType] = useState("WEB");

  // Subscriptions & Devices
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [subscribingPlanId, setSubscribingPlanId] = useState<string | null>(null);

  // New Device Form
  const [newDeviceName, setNewDeviceName] = useState("");
  const [newDeviceFingerprint, setNewDeviceFingerprint] = useState("");
  const [newDevicePublicKey, setNewDevicePublicKey] = useState("");
  const [activatedLicense, setActivatedLicense] = useState<string | null>(null);

  // Copied State
  const [copiedOrgId, setCopiedOrgId] = useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedOrgId(id);
    setTimeout(() => {
      setCopiedOrgId((current) => (current === id ? null : current));
    }, 2000);
  };

  useEffect(() => {
    const savedToken = localStorage.getItem("vex_token");
    const savedUser = localStorage.getItem("vex_user");
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }

    const handleAuthExpired = () => {
      setToken(null);
      setUser(null);
      setAuthError("Your session has expired. Please sign in again.");
    };

    window.addEventListener("vex_auth_expired", handleAuthExpired);
    return () => {
      window.removeEventListener("vex_auth_expired", handleAuthExpired);
    };
  }, []);

  useEffect(() => {
    if (token) {
      fetchOrganizations();
      fetchApplications();
      fetchPlans();
    }
  }, [token]);

  const fetchPlans = async () => {
    try {
      const res = await api.get("/plans");
      setPlans(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchOrgDetails = async (orgId: string) => {
    loadOrgMembers(orgId);
    loadOrgSubscriptions(orgId);
    loadOrgDevices(orgId);
  };

  const loadOrgSubscriptions = async (orgId: string) => {
    try {
      const res = await api.get(`/organizations/${orgId}/subscriptions`);
      setSubscriptions(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const loadOrgDevices = async (orgId: string) => {
    try {
      const res = await api.get(`/organizations/${orgId}/devices`);
      setDevices(res.data);
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

  const handleRegisterDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg) return;
    try {
      await api.post("/devices/register", {
        organization_id: selectedOrg.id,
        name: newDeviceName,
        fingerprint: newDeviceFingerprint,
        public_key: newDevicePublicKey,
      });
      alert("Physical device registered successfully!");
      setNewDeviceName("");
      setNewDeviceFingerprint("");
      setNewDevicePublicKey("");
      loadOrgDevices(selectedOrg.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to register device");
    }
  };

  const handleIssueLicense = async (deviceId: string, appId: string) => {
    try {
      const res = await api.post("/licenses/activate", {
        device_id: deviceId,
        application_id: appId,
      });
      setActivatedLicense(res.data.signed_payload);
      alert("Ed25519 Offline License activated successfully!");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to activate license. Check device seat quota.");
    }
  };

  const fetchOrganizations = async () => {
    try {
      const res = await api.get("/organizations");
      setOrganizations(res.data);
      if (res.data.length > 0 && !selectedOrg) {
        setSelectedOrg(res.data[0]);
        fetchOrgDetails(res.data[0].id);
      }
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
        // Auto login after registration
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
    if (!newOrgName) return;
    try {
      const res = await api.post("/organizations", {
        name: newOrgName,
        registration_number: newOrgReg || undefined,
      });
      setNewOrgName("");
      setNewOrgReg("");
      fetchOrganizations();
      setSelectedOrg(res.data);
      loadOrgMembers(res.data.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create organization");
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

  const handleRegisterApp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAppCode || !newAppName) return;
    try {
      await api.post("/applications", {
        code: newAppCode,
        name: newAppName,
        type: newAppType,
      });
      setNewAppCode("");
      setNewAppName("");
      fetchApplications();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to register application");
    }
  };

  // ---------------- Authentication Screen ----------------
  if (!token || !user) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-6 text-white">
        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center space-x-3 mb-6">
            <div className="h-10 w-10 bg-indigo-600 rounded-xl flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30">
              V
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">VEX IAM</h1>
              <p className="text-xs text-slate-400">Vexxero Identity & Access Management</p>
            </div>
          </div>

          <div className="flex border-b border-slate-800 mb-6">
            <button
              onClick={() => {
                setIsLoginMode(true);
                setAuthError("");
              }}
              className={`flex-1 pb-3 text-sm font-semibold transition-colors ${
                isLoginMode
                  ? "border-b-2 border-indigo-500 text-indigo-400"
                  : "text-slate-400 hover:text-slate-200"
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
                !isLoginMode
                  ? "border-b-2 border-indigo-500 text-indigo-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Register Identity
            </button>
          </div>

          {authError && (
            <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg flex items-center text-sm text-rose-400">
              <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
              <span>{authError}</span>
            </div>
          )}

          <form onSubmit={handleAuth} className="space-y-4">
            {!isLoginMode && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    First Name
                  </label>
                  <input
                    type="text"
                    required
                    value={authFirstName}
                    onChange={(e) => setAuthFirstName(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Alex"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Last Name
                  </label>
                  <input
                    type="text"
                    required
                    value={authLastName}
                    onChange={(e) => setAuthLastName(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Smith"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Global VEX Email
              </label>
              <input
                type="email"
                required
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={authLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg text-sm transition-all duration-200 flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/30"
            >
              <span>{authLoading ? "Authenticating..." : isLoginMode ? "Sign In" : "Create Account"}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-slate-500">
            Secured by Argon2id & Ed25519 token signatures.
          </p>
        </div>
      </div>
    );
  }

  // ---------------- Dashboard Screen ----------------
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 bg-indigo-600 rounded-xl flex items-center justify-center font-bold text-white shadow-md shadow-indigo-500/20">
              V
            </div>
            <span className="font-bold text-lg tracking-tight">VEX IAM</span>
          </div>

          <nav className="flex space-x-1">
            <button
              onClick={() => setActiveTab("individual")}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center space-x-2 ${
                activeTab === "individual"
                  ? "bg-slate-800 text-indigo-400 border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <UserCheck className="w-4 h-4" />
              <span>Individual Identity</span>
            </button>
            <button
              onClick={() => setActiveTab("organizations")}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center space-x-2 ${
                activeTab === "organizations"
                  ? "bg-slate-800 text-indigo-400 border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Building2 className="w-4 h-4" />
              <span>Business Entities</span>
            </button>
            <button
              onClick={() => setActiveTab("apps")}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center space-x-2 ${
                activeTab === "apps"
                  ? "bg-slate-800 text-indigo-400 border border-slate-700"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Application Catalog</span>
            </button>
          </nav>
        </div>

        <div className="flex items-center space-x-4">
          <div className="text-right">
            <p className="text-xs font-semibold text-slate-200">
              {user.profile?.first_name} {user.profile?.last_name}
            </p>
            <p className="text-[11px] text-slate-400">{user.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
            title="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-8 max-w-7xl mx-auto w-full">
        {/* Tab 1: Individual Identity */}
        {activeTab === "individual" && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h2 className="text-lg font-bold mb-4 flex items-center space-x-2 text-white">
                <ShieldCheck className="w-5 h-5 text-indigo-400" />
                <span>Global Individual Identity</span>
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                  <p className="text-xs text-slate-400 mb-1">User Identifier (UUID)</p>
                  <p className="font-mono text-xs text-indigo-300 break-all">{user.id}</p>
                </div>
                <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                  <p className="text-xs text-slate-400 mb-1">Account Status</p>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {user.status}
                  </span>
                </div>
                <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
                  <p className="text-xs text-slate-400 mb-1">Email Verification</p>
                  {user.email_verified ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Verified
                    </span>
                  ) : (
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        Unverified
                      </span>
                      <button
                        onClick={async () => {
                          try {
                            await api.post("/auth/resend-verification", { email: user.email });
                            alert("Verification link sent! Check your email inbox.");
                          } catch (err: any) {
                            alert(err.response?.data?.detail || "Failed to resend verification email");
                          }
                        }}
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 underline font-medium ml-2"
                      >
                        Resend Email
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h3 className="text-base font-bold text-white mb-3">Organization Memberships</h3>
              <p className="text-xs text-slate-400 mb-4">
                Businesses where your personal identity has active workspace access.
              </p>
              {organizations.length === 0 ? (
                <p className="text-sm text-slate-500">You are not a member of any business entity yet.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {organizations.map((org) => (
                    <div
                      key={org.id}
                      className="p-4 bg-slate-800/40 border border-slate-700 rounded-xl flex items-center justify-between"
                    >
                      <div>
                        <h4 className="font-semibold text-sm text-white">{org.name}</h4>
                        <p className="text-xs text-slate-400">
                          {org.registration_number || "No registration number"}
                        </p>
                      </div>
                      <span className="text-xs bg-indigo-500/10 text-indigo-400 px-2.5 py-1 rounded-full border border-indigo-500/20">
                        {org.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Organizations & User Pool */}
        {activeTab === "organizations" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left: Organization list & Creation */}
            <div className="space-y-6">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <h3 className="text-base font-bold text-white mb-4">Establish Business Entity</h3>
                <form onSubmit={handleCreateOrg} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Business Name</label>
                    <input
                      type="text"
                      required
                      value={newOrgName}
                      onChange={(e) => setNewOrgName(e.target.value)}
                      placeholder="e.g. B & B Cafe"
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">
                      Registration Number
                    </label>
                    <input
                      type="text"
                      value={newOrgReg}
                      onChange={(e) => setNewOrgReg(e.target.value)}
                      placeholder="e.g. REG-987654"
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2 rounded-lg text-xs transition-colors flex items-center justify-center space-x-2"
                  >
                    <PlusCircle className="w-4 h-4" />
                    <span>Create Organization (As Owner)</span>
                  </button>
                </form>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <h3 className="text-base font-bold text-white mb-3">Your Organizations</h3>
                <div className="space-y-2">
                  {organizations.map((org) => (
                    <div
                      key={org.id}
                      onClick={() => {
                        setSelectedOrg(org);
                        fetchOrgDetails(org.id);
                        setGeneratedInviteToken(null);
                      }}
                      className={`w-full text-left p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between group ${
                        selectedOrg?.id === org.id
                          ? "bg-indigo-600/10 border-indigo-500/50 text-indigo-300"
                          : "bg-slate-800/40 border-slate-800 text-slate-300 hover:bg-slate-800"
                      }`}
                    >
                      <div className="min-w-0 pr-2 flex-1">
                        <p className="font-semibold text-sm truncate">{org.name}</p>
                        <p className="text-[11px] text-slate-500 font-mono truncate">{org.id}</p>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          copyToClipboard(org.id, org.id);
                        }}
                        title="Copy Organization ID"
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700/60 transition-colors flex items-center gap-1 shrink-0"
                      >
                        {copiedOrgId === org.id ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-[10px] text-emerald-400 font-medium">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span className="text-[10px] hidden group-hover:inline">Copy</span>
                          </>
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right: User Pool & Members */}
            <div className="lg:col-span-2 space-y-6">
              {selectedOrg ? (
                <>
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                    <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-800">
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="text-xl font-bold text-white">{selectedOrg.name}</h2>
                          <button
                            type="button"
                            onClick={() => copyToClipboard(selectedOrg.id, `header-${selectedOrg.id}`)}
                            title="Copy Organization ID"
                            className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white border border-slate-700 text-xs transition-colors"
                          >
                            {copiedOrgId === `header-${selectedOrg.id}` ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-400" />
                                <span className="text-[11px] text-emerald-400 font-medium">Copied ID</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                <span className="text-[11px] font-mono">{selectedOrg.id.slice(0, 8)}...</span>
                              </>
                            )}
                          </button>
                        </div>
                        <p className="text-xs text-slate-400">Organization User Pool & Access</p>
                      </div>
                      <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-semibold">
                        {selectedOrg.status}
                      </span>
                    </div>

                    {/* Invite Member */}
                    <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 mb-6">
                      <h4 className="text-xs font-bold text-slate-300 mb-3 flex items-center space-x-2">
                        <Mail className="w-4 h-4 text-indigo-400" />
                        <span>Invite Individual VEX IAM Identity</span>
                      </h4>
                      <form onSubmit={handleInvite} className="flex gap-3">
                        <input
                          type="email"
                          required
                          value={inviteEmail}
                          onChange={(e) => setInviteEmail(e.target.value)}
                          placeholder="employee@domain.com"
                          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                        <select
                          value={inviteRole}
                          onChange={(e) => setInviteRole(e.target.value)}
                          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                        >
                          <option value="MEMBER">MEMBER</option>
                          <option value="ADMIN">ADMIN</option>
                        </select>
                        <button
                          type="submit"
                          className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-xs font-semibold"
                        >
                          Send Invitation
                        </button>
                      </form>

                      {generatedInviteToken && (
                        <div className="mt-3 p-3 bg-indigo-950/50 border border-indigo-800/50 rounded-lg text-xs">
                          <p className="text-indigo-300 font-semibold mb-1">
                            Secure Invitation Token Generated:
                          </p>
                          <p className="font-mono text-[11px] text-slate-300 break-all select-all">
                            {generatedInviteToken}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Member Table */}
                    <h4 className="text-sm font-bold text-slate-200 mb-3">
                      Active User Pool ({orgMembers.length})
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-400">
                            <th className="py-2.5">User</th>
                            <th className="py-2.5">Email</th>
                            <th className="py-2.5">Organization Role</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                          {orgMembers.map((m) => (
                            <tr key={m.id} className="hover:bg-slate-800/30">
                              <td className="py-3 font-medium text-white">
                                {m.user?.profile?.first_name} {m.user?.profile?.last_name || "—"}
                              </td>
                              <td className="py-3 text-slate-400">{m.user?.email}</td>
                              <td className="py-3">
                                <span
                                  className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                                    m.role === "OWNER"
                                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                      : m.role === "ADMIN"
                                      ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                                      : "bg-slate-700/50 text-slate-300 border border-slate-600"
                                  }`}
                                >
                                  {m.role}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Subscriptions & Commercial Plans Management */}
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-base font-bold text-white flex items-center gap-2">
                          <Layers className="w-4 h-4 text-indigo-400" />
                          <span>Active Subscriptions & Quotas</span>
                        </h3>
                        <p className="text-xs text-slate-400">
                          Commercial application entitlements, user seat limits, and device quotas.
                        </p>
                      </div>
                    </div>

                    {subscriptions.length === 0 ? (
                      <div className="p-4 bg-slate-800/30 border border-slate-800 rounded-xl text-center">
                        <p className="text-xs text-slate-400 mb-4">No active subscriptions for this organization.</p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        {subscriptions.map((sub) => (
                          <div
                            key={sub.id}
                            className="p-4 bg-slate-800/50 border border-slate-700/60 rounded-xl flex flex-col justify-between"
                          >
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-mono font-bold text-indigo-400">
                                  {sub.plan?.code}
                                </span>
                                <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-semibold">
                                  {sub.status}
                                </span>
                              </div>
                              <h4 className="text-sm font-semibold text-white mb-1">{sub.plan?.name}</h4>
                              <p className="text-xs text-slate-400 mb-3">{sub.plan?.description}</p>
                            </div>
                            <div className="pt-3 border-t border-slate-700/50 flex items-center justify-between text-xs text-slate-300">
                              <span>Users: <strong>{sub.plan?.user_seats} seats</strong></span>
                              <span>Terminals: <strong>{sub.plan?.device_seats} devices</strong></span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Available Plans to Buy / Subscribe */}
                    <div className="border-t border-slate-800 pt-5">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                        Subscribe to an Ecosystem Plan
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {plans.map((p) => (
                          <div
                            key={p.id}
                            className="p-3.5 bg-slate-800/30 border border-slate-700/40 rounded-xl flex flex-col justify-between hover:border-slate-600 transition"
                          >
                            <div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-mono text-[10px] text-indigo-400">{p.code}</span>
                              </div>
                              <h5 className="font-semibold text-xs text-white">{p.name}</h5>
                              <p className="text-[11px] text-slate-400 my-1">{p.description}</p>
                              <div className="text-[10px] text-slate-300 space-y-0.5 my-2">
                                <div>• {p.user_seats} User Seats</div>
                                <div>• {p.device_seats} Device Terminal Quota</div>
                              </div>
                            </div>
                            <button
                              onClick={() => handleBuySubscription(p.id)}
                              disabled={subscribingPlanId === p.id}
                              className="w-full mt-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 text-white rounded-lg text-xs font-semibold py-1.5 transition"
                            >
                              {subscribingPlanId === p.id ? "Activating..." : "Subscribe / Purchase"}
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Device Licensing & Terminal Activations */}
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-base font-bold text-white flex items-center gap-2">
                          <Laptop className="w-4 h-4 text-cyan-400" />
                          <span>Hardware Terminals & Offline Licenses</span>
                        </h3>
                        <p className="text-xs text-slate-400">
                          Register POS cashiers, tablets, and kiosks with 30-day offline Ed25519 cryptographic licenses.
                        </p>
                      </div>
                    </div>

                    {/* Registered Devices List */}
                    {devices.length === 0 ? (
                      <div className="p-4 bg-slate-800/30 border border-slate-800 rounded-xl text-center mb-6">
                        <p className="text-xs text-slate-400">No physical devices registered for this organization yet.</p>
                      </div>
                    ) : (
                      <div className="space-y-3 mb-6">
                        {devices.map((dev) => (
                          <div
                            key={dev.id}
                            className="p-4 bg-slate-800/40 border border-slate-700/60 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                          >
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="font-semibold text-sm text-white">{dev.name}</h4>
                                <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.2 rounded font-semibold">
                                  {dev.status}
                                </span>
                              </div>
                              <p className="font-mono text-[11px] text-slate-400 mt-1">
                                Fingerprint: {dev.fingerprint}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              {applications.length > 0 && (
                                <button
                                  onClick={() => handleIssueLicense(dev.id, applications[0].id)}
                                  className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm"
                                >
                                  <KeyRound className="w-3.5 h-3.5" />
                                  <span>Issue Offline License</span>
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Activated License Display */}
                    {activatedLicense && (
                      <div className="mb-6 p-4 bg-cyan-950/40 border border-cyan-800/50 rounded-xl">
                        <p className="text-xs font-bold text-cyan-300 mb-1 flex items-center gap-1.5">
                          <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                          <span>Generated Cryptographic Ed25519 Offline License:</span>
                        </p>
                        <p className="text-[11px] text-slate-300 mb-2">
                          Install this license on the VEX POS terminal. It verifies offline cryptographically for 30 days.
                        </p>
                        <textarea
                          readOnly
                          rows={3}
                          value={activatedLicense}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 font-mono text-[11px] text-cyan-200 select-all"
                        />
                      </div>
                    )}

                    {/* Register New Hardware Terminal Form */}
                    <div className="border-t border-slate-800 pt-5">
                      <h4 className="text-xs font-bold text-slate-300 mb-3 flex items-center gap-1.5">
                        <PlusCircle className="w-4 h-4 text-indigo-400" />
                        <span>Register Hardware Terminal</span>
                      </h4>
                      <form onSubmit={handleRegisterDevice} className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <input
                          type="text"
                          required
                          value={newDeviceName}
                          onChange={(e) => setNewDeviceName(e.target.value)}
                          placeholder="Device Name (e.g. Counter POS #1)"
                          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white"
                        />
                        <input
                          type="text"
                          required
                          value={newDeviceFingerprint}
                          onChange={(e) => setNewDeviceFingerprint(e.target.value)}
                          placeholder="Hardware Fingerprint (e.g. HW-8934FA-X)"
                          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white"
                        />
                        <input
                          type="text"
                          required
                          value={newDevicePublicKey}
                          onChange={(e) => setNewDevicePublicKey(e.target.value)}
                          placeholder="Device Ed25519 Public Key"
                          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono"
                        />
                        <button
                          type="submit"
                          className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold py-2 transition"
                        >
                          Register Terminal
                        </button>
                      </form>
                    </div>
                  </div>
                </>
              ) : (
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
                  Select an organization to view its user pool.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: Applications Catalog */}
        {activeTab === "apps" && (
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <Layers className="w-5 h-5 text-indigo-400" />
                    <span>Official Vexxero Ecosystem Applications</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Verified first-party software authorized and integrated with VEX IAM OAuth 2.1 / OIDC. Managed centrally by Vexxero Technologies.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Verified Ecosystem
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {applications.map((app) => (
                  <div
                    key={app.id}
                    className="p-5 bg-slate-800/40 border border-slate-700/60 rounded-xl hover:border-slate-600 transition flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded border border-indigo-500/20">
                          {app.code}
                        </span>
                        <span className="text-[11px] font-medium text-slate-400 px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                          {app.type}
                        </span>
                      </div>
                      <h3 className="font-semibold text-base text-white mb-2">{app.name}</h3>
                      <p className="text-xs text-slate-400 leading-relaxed mb-4">
                        {app.description || "Official client integrated with VEX IAM authentication and access control."}
                      </p>
                    </div>

                    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
                      <span className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        VEX IAM Ready
                      </span>
                      <span className="font-mono text-[10px]">Ed25519 / OIDC</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
