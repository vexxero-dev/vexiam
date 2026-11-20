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
  Trash2,
  UserPlus,
  X,
  Cpu,
  Activity,
  Clock,
  MapPin,
  Edit2,
  Globe,
  Store,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Sparkles,
  Cloud,
  CloudOff,
  Lock,
  FileText,
  Settings as SettingsIcon,
} from "lucide-react";

import {
  User,
  Organization,
  Member,
  Application,
  Plan,
  Subscription,
  Device,
  OrgLocation,
  ApplicationRole,
  ApplicationAssignment,
  ActivatedSyncTicket,
  MainNavSection,
} from "@/types";

import { Sidebar } from "@/components/dashboard/Sidebar";
import { Topbar } from "@/components/dashboard/Topbar";
import { SetupChecklist } from "@/components/dashboard/SetupChecklist";
import { ExecutiveOverviewView } from "@/components/dashboard/ExecutiveOverviewView";
import { LocationManagementView } from "@/components/dashboard/LocationManagementView";
import { TerminalManagementView } from "@/components/dashboard/TerminalManagementView";
import { SubscriptionManagementView } from "@/components/dashboard/SubscriptionManagementView";
import { TeamManagementView } from "@/components/dashboard/TeamManagementView";
import { BusinessEntitiesView } from "@/components/dashboard/BusinessEntitiesView";
import { ApplicationCatalogView } from "@/components/dashboard/ApplicationCatalogView";
import { IndividualIdentityView } from "@/components/dashboard/IndividualIdentityView";

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
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("MEMBER");
  const [generatedInviteToken, setGeneratedInviteToken] = useState<string | null>(null);

  // Applications
  const [applications, setApplications] = useState<Application[]>([]);

  // Locations
  const [locations, setLocations] = useState<OrgLocation[]>([]);
  const [locationModalOpen, setLocationModalOpen] = useState(false);
  const [editingLocation, setEditingLocation] = useState<OrgLocation | null>(null);
  const [locCode, setLocCode] = useState("");
  const [locName, setLocName] = useState("");
  const [locDescription, setLocDescription] = useState("");
  const [locAddress1, setLocAddress1] = useState("");
  const [locAddress2, setLocAddress2] = useState("");
  const [locCity, setLocCity] = useState("");
  const [locState, setLocState] = useState("");
  const [locPostal, setLocPostal] = useState("");
  const [locCountry, setLocCountry] = useState("LK");
  const [locTimezone, setLocTimezone] = useState("Asia/Colombo");
  const [locStatus, setLocStatus] = useState("ACTIVE");
  const [locSyncEnabled, setLocSyncEnabled] = useState(true);
  const [locPosModePolicy, setLocPosModePolicy] = useState<"ANY_ALLOWED" | "LOCAL_ONLY" | "CLOUD_ONLY">("ANY_ALLOWED");
  const [locPosDefaultMode, setLocPosDefaultMode] = useState<"LOCAL" | "CLOUD">("LOCAL");
  const [locLoading, setLocLoading] = useState(false);
  const [locError, setLocError] = useState("");

  // Subscriptions & Devices
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [subscribingPlanId, setSubscribingPlanId] = useState<string | null>(null);

  // Application Assignments (Seats)
  const [assignments, setAssignments] = useState<ApplicationAssignment[]>([]);
  const [assigningApp, setAssigningApp] = useState<{ id: string; name: string } | null>(null);
  const [assignUserId, setAssignUserId] = useState<string>("");
  const [assignRoleId, setAssignRoleId] = useState<string>("");
  const [availableRoles, setAvailableRoles] = useState<ApplicationRole[]>([]);
  const [assignLoading, setAssignLoading] = useState(false);

  // New Device Form
  const [newDeviceName, setNewDeviceName] = useState("");
  const [newDeviceFingerprint, setNewDeviceFingerprint] = useState("");
  const [newDevicePublicKey, setNewDevicePublicKey] = useState("");
  const [activatedLicense, setActivatedLicense] = useState<string | null>(null);
  const [activatedSyncTicket, setActivatedSyncTicket] = useState<ActivatedSyncTicket | null>(null);
  const [syncActivatingDeviceId, setSyncActivatingDeviceId] = useState<string | null>(null);

  // Copied State
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => {
      setCopiedId((current) => (current === id ? null : current));
    }, 2000);
  };

  const formatHeartbeatTime = (timestamp?: string | null) => {
    if (!timestamp) return "Never";
    try {
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) return "Unknown";
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSecs = Math.max(0, Math.floor(diffMs / 1000));

      if (diffSecs < 60) return "Just now";
      const diffMins = Math.floor(diffSecs / 60);
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      return date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "Unknown";
    }
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
      setLocations([]);
      setSubscriptions([]);
      setDevices([]);
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
    loadOrgLocations(orgId);
    loadOrgSubscriptions(orgId);
    loadOrgDevices(orgId);
    loadOrgAssignments(orgId);
  };

  const loadOrgLocations = async (orgId: string) => {
    try {
      const res = await api.get(`/organizations/${orgId}/locations`);
      setLocations(res.data);
    } catch (e) {
      console.error(e);
      setLocations([]);
    }
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
      if (selectedOrg) {
        loadOrgDevices(selectedOrg.id);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to activate license. Check device seat quota.");
    }
  };

  const handleActivatePosSync = async (deviceId: string, appCode: string = "VEX-POS") => {
    setSyncActivatingDeviceId(deviceId);
    try {
      const res = await api.post(`/devices/${deviceId}/sync-activate`, {
        application_code: appCode,
      });
      setActivatedSyncTicket(res.data);
      alert("POS Cloud Sync successfully activated via VEX IAM authority!");
      if (selectedOrg) {
        loadOrgDevices(selectedOrg.id);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to activate POS cloud sync. Ensure device is assigned to an active location and has an active subscription.");
    } finally {
      setSyncActivatingDeviceId(null);
    }
  };

  const handleDeactivatePosSync = async (deviceId: string) => {
    if (!confirm("Are you sure you want to disable POS Cloud Sync for this device?")) {
      return;
    }
    setSyncActivatingDeviceId(deviceId);
    try {
      await api.post(`/devices/${deviceId}/sync-deactivate`);
      alert("POS Cloud Sync disabled successfully.");
      if (activatedSyncTicket?.device_id === deviceId) {
        setActivatedSyncTicket(null);
      }
      if (selectedOrg) {
        loadOrgDevices(selectedOrg.id);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to disable POS cloud sync.");
    } finally {
      setSyncActivatingDeviceId(null);
    }
  };

  const handleReassignDevice = async (deviceId: string, targetLocationId: string) => {
    if (!selectedOrg) return;
    try {
      await api.post(`/devices/${deviceId}/reassign`, {
        target_location_id: targetLocationId ? targetLocationId : null,
      });
      loadOrgDevices(selectedOrg.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to reassign device.");
    }
  };

  const handleUpdateDeviceMenuMode = async (deviceId: string, newMode: string) => {
    if (!selectedOrg) return;
    try {
      await api.post(`/devices/${deviceId}/menu-mode?mode=${encodeURIComponent(newMode)}`);
      loadOrgDevices(selectedOrg.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to update terminal operating mode.");
    }
  };

  const handleDeleteDevice = async (deviceId: string, deviceName: string) => {
    if (!selectedOrg) return;
    if (!confirm(`Are you sure you want to delete terminal "${deviceName}"? This will revoke active licenses and remove the device registration.`)) {
      return;
    }
    try {
      await api.delete(`/devices/${deviceId}`);
      loadOrgDevices(selectedOrg.id);
      loadOrgSubscriptions(selectedOrg.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to delete device");
    }
  };

  const openCreateLocationModal = () => {
    setEditingLocation(null);
    setLocCode("");
    setLocName("");
    setLocDescription("");
    setLocAddress1("");
    setLocAddress2("");
    setLocCity("");
    setLocState("");
    setLocPostal("");
    setLocCountry("LK");
    setLocTimezone("Asia/Colombo");
    setLocStatus("ACTIVE");
    setLocSyncEnabled(true);
    setLocPosModePolicy("ANY_ALLOWED");
    setLocPosDefaultMode("LOCAL");
    setLocError("");
    setLocationModalOpen(true);
  };

  const openEditLocationModal = (loc: OrgLocation) => {
    setEditingLocation(loc);
    setLocCode(loc.code);
    setLocName(loc.name);
    setLocDescription(loc.description || "");
    setLocAddress1(loc.address_line1 || "");
    setLocAddress2(loc.address_line2 || "");
    setLocCity(loc.city || "");
    setLocState(loc.state_province || "");
    setLocPostal(loc.postal_code || "");
    setLocCountry(loc.country_code || "LK");
    setLocTimezone(loc.timezone || "Asia/Colombo");
    setLocStatus(loc.status || "ACTIVE");
    setLocPosModePolicy(loc.pos_mode_policy || "ANY_ALLOWED");
    setLocPosDefaultMode(loc.pos_default_mode || "LOCAL");
    const meta = loc.metadata as Record<string, any> | undefined;
    setLocSyncEnabled(loc.pos_sync_allowed !== undefined ? loc.pos_sync_allowed : (meta ? meta["pos.sync"] !== false && meta["cloud_sync"] !== false : true));
    setLocError("");
    setLocationModalOpen(true);
  };

  const handleSaveLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg) return;
    setLocError("");
    setLocLoading(true);

    const metaPayload = {
      ...((editingLocation?.metadata as Record<string, any>) || {}),
      "pos.sync": locSyncEnabled,
      "cloud_sync": locSyncEnabled,
    };

    try {
      if (editingLocation) {
        await api.put(`/locations/${editingLocation.id}`, {
          name: locName.trim(),
          description: locDescription.trim() || null,
          address_line1: locAddress1.trim() || null,
          address_line2: locAddress2.trim() || null,
          city: locCity.trim() || null,
          state_province: locState.trim() || null,
          postal_code: locPostal.trim() || null,
          country_code: locCountry.trim().toUpperCase() || null,
          timezone: locTimezone.trim() || "UTC",
          status: locStatus,
          metadata: metaPayload,
        });

        await api.put(`/locations/${editingLocation.id}/pos-policy`, {
          pos_mode_policy: locPosModePolicy,
          pos_default_mode: locPosDefaultMode,
          pos_sync_allowed: locSyncEnabled,
        });
      } else {
        const createdLoc = await api.post(`/organizations/${selectedOrg.id}/locations`, {
          code: locCode.trim().toUpperCase(),
          name: locName.trim(),
          description: locDescription.trim() || null,
          address_line1: locAddress1.trim() || null,
          address_line2: locAddress2.trim() || null,
          city: locCity.trim() || null,
          state_province: locState.trim() || null,
          postal_code: locPostal.trim() || null,
          country_code: locCountry.trim().toUpperCase() || null,
          timezone: locTimezone.trim() || "Asia/Colombo",
          status: locStatus,
          metadata: metaPayload,
        });

        await api.put(`/locations/${createdLoc.data.id}/pos-policy`, {
          pos_mode_policy: locPosModePolicy,
          pos_default_mode: locPosDefaultMode,
          pos_sync_allowed: locSyncEnabled,
        });
      }
      setLocationModalOpen(false);
      loadOrgLocations(selectedOrg.id);
    } catch (err: any) {
      setLocError(err.response?.data?.detail || "Failed to save location details.");
    } finally {
      setLocLoading(false);
    }
  };

  const handleArchiveLocation = async (loc: OrgLocation) => {
    if (!selectedOrg) return;
    if (!confirm(`Are you sure you want to archive location "${loc.name}" (${loc.code})? Hardware POS terminals assigned to this branch will no longer authorize sync.`)) {
      return;
    }
    try {
      await api.delete(`/locations/${loc.id}`);
      loadOrgLocations(selectedOrg.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to archive location.");
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
    if (!newOrgName) return;
    try {
      const res = await api.post("/organizations", {
        name: newOrgName,
        registration_number: newOrgReg || undefined,
      });
      setNewOrgName("");
      setNewOrgReg("");
      setCreateOrgModalOpen(false);
      fetchOrganizations();
      setSelectedOrg(res.data);
      loadOrgMembers(res.data.id);
      setActiveSection("org_locations");
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
            hasLocation={locations.length > 0}
            hasTerminal={devices.length > 0}
            hasSubscription={subscriptions.length > 0}
            onNavigateSection={(sec) => setActiveSection(sec)}
          />

          {/* SECTION 1: Overview */}
          {activeSection === "overview" && (
            <ExecutiveOverviewView
              selectedOrg={selectedOrg}
              members={orgMembers}
              locations={locations}
              devices={devices}
              subscriptions={subscriptions}
              onNavigateSection={(sec) => setActiveSection(sec)}
              onOpenCreateLocation={openCreateLocationModal}
              formatHeartbeatTime={formatHeartbeatTime}
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
              locations={locations}
              devices={devices}
              members={orgMembers}
            />
          )}

          {/* SECTION 4: Application Catalog */}
          {activeSection === "app_catalog" && (
            <ApplicationCatalogView applications={applications} />
          )}

          {/* SECTION 5: Store Locations */}
          {activeSection === "org_locations" && (
            <LocationManagementView
              locations={locations}
              devices={devices}
              copiedId={copiedId}
              onCopy={copyToClipboard}
              onOpenCreateModal={openCreateLocationModal}
              onOpenEditModal={openEditLocationModal}
              onArchiveLocation={handleArchiveLocation}
              onViewTerminalsForLocation={(locId) => {
                setActiveSection("org_terminals");
              }}
            />
          )}

          {/* SECTION 6: Hardware Terminals */}
          {activeSection === "org_terminals" && (
            <TerminalManagementView
              devices={devices}
              locations={locations}
              applications={applications}
              activatedLicense={activatedLicense}
              activatedSyncTicket={activatedSyncTicket}
              syncActivatingDeviceId={syncActivatingDeviceId}
              copiedId={copiedId}
              onCopy={copyToClipboard}
              onRegisterDevice={handleRegisterDevice}
              newDeviceName={newDeviceName}
              setNewDeviceName={setNewDeviceName}
              newDeviceFingerprint={newDeviceFingerprint}
              setNewDeviceFingerprint={setNewDeviceFingerprint}
              newDevicePublicKey={newDevicePublicKey}
              setNewDevicePublicKey={setNewDevicePublicKey}
              onReassignDevice={handleReassignDevice}
              onUpdateMenuMode={handleUpdateDeviceMenuMode}
              onIssueLicense={handleIssueLicense}
              onActivateSync={handleActivatePosSync}
              onDeactivateSync={handleDeactivatePosSync}
              onDeleteDevice={handleDeleteDevice}
              formatHeartbeatTime={formatHeartbeatTime}
            />
          )}

          {/* SECTION 7: Subscriptions & Quotas */}
          {activeSection === "org_subscriptions" && (
            <SubscriptionManagementView
              subscriptions={subscriptions}
              plans={plans}
              applications={applications}
              assignments={assignments}
              devices={devices}
              subscribingPlanId={subscribingPlanId}
              onBuySubscription={handleBuySubscription}
              onOpenAssignModal={openAssignModal}
              onRevokeAssignment={handleRevokeAssignment}
              onNavigateToTerminals={() => setActiveSection("org_terminals")}
            />
          )}

          {/* SECTION 8: Team & User Pool */}
          {activeSection === "org_team" && (
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

          {/* SECTION 9: Security & Access (Administration) */}
          {activeSection === "security" && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Lock className="w-5 h-5 text-indigo-400" />
                <span>Security Policies & Key Management</span>
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                VEX IAM issues Ed25519 elliptic-curve cryptographic tokens for local workstation POS activation and OAuth 2.1 authorization.
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

          {/* SECTION 10: Audit Logs (Administration) */}
          {activeSection === "audit" && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-indigo-400" />
                <span>Audit & Security Ledger</span>
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Immutable audit ledger tracking terminal registrations, offline license generation, and organization role changes.
              </p>
              <div className="p-8 bg-slate-950 rounded-xl border border-slate-800 text-center text-xs text-slate-500">
                Audit ledger live stream active. All device registration and sync activation events are signed and recorded.
              </div>
            </div>
          )}

          {/* SECTION 11: Settings */}
          {activeSection === "settings" && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
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
                  disabled={!newOrgName.trim()}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white text-xs font-semibold py-2.5 rounded-xl transition shadow-sm shadow-indigo-600/30"
                >
                  Establish Entity
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Location Modal */}
      {locationModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Store className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">
                  {editingLocation ? `Edit Location: ${editingLocation.code}` : "Establish Store Location"}
                </h3>
              </div>
              <button
                onClick={() => setLocationModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {locError && (
              <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center text-xs text-rose-400">
                <AlertCircle className="w-4 h-4 mr-2 shrink-0" />
                <span>{locError}</span>
              </div>
            )}

            <form onSubmit={handleSaveLocation} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Location Code *</label>
                  <input
                    type="text"
                    required
                    disabled={!!editingLocation}
                    value={locCode}
                    onChange={(e) => setLocCode(e.target.value.toUpperCase())}
                    placeholder="MAIN-OUTLET"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-emerald-500 disabled:opacity-50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Location Display Name *</label>
                  <input
                    type="text"
                    required
                    value={locName}
                    onChange={(e) => setLocName(e.target.value)}
                    placeholder="Colombo 03 Branch"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Description</label>
                <input
                  type="text"
                  value={locDescription}
                  onChange={(e) => setLocDescription(e.target.value)}
                  placeholder="Primary café outlet & takeout counter"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Address Line 1</label>
                  <input
                    type="text"
                    value={locAddress1}
                    onChange={(e) => setLocAddress1(e.target.value)}
                    placeholder="No. 45 Galle Road"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">City</label>
                  <input
                    type="text"
                    value={locCity}
                    onChange={(e) => setLocCity(e.target.value)}
                    placeholder="Colombo"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Country Code</label>
                  <input
                    type="text"
                    maxLength={2}
                    value={locCountry}
                    onChange={(e) => setLocCountry(e.target.value.toUpperCase())}
                    placeholder="LK"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Timezone</label>
                  <input
                    type="text"
                    value={locTimezone}
                    onChange={(e) => setLocTimezone(e.target.value)}
                    placeholder="Asia/Colombo"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Branch Status</label>
                  <select
                    value={locStatus}
                    onChange={(e) => setLocStatus(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="ARCHIVED">ARCHIVED</option>
                  </select>
                </div>
              </div>

              {/* Cloud Sync and POS Mode Policy */}
              <div className="pt-2 border-t border-slate-800 space-y-3">
                <div className="flex items-center justify-between p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <div>
                    <div className="text-xs font-semibold text-white">Authorize Cloud POS Synchronization</div>
                    <div className="text-[10px] text-slate-400">Allow terminals at this branch to sync transactions with VEX Cloud</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={locSyncEnabled}
                    onChange={(e) => setLocSyncEnabled(e.target.checked)}
                    className="w-4 h-4 rounded text-emerald-600 focus:ring-0 cursor-pointer"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Terminal Mode Policy</label>
                    <select
                      value={locPosModePolicy}
                      onChange={(e) => setLocPosModePolicy(e.target.value as any)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                    >
                      <option value="ANY_ALLOWED">ANY_ALLOWED (Operator Choice)</option>
                      <option value="LOCAL_ONLY">LOCAL_ONLY (Enforce Standalone)</option>
                      <option value="CLOUD_ONLY">CLOUD_ONLY (Enforce Centralized)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Default Menu Mode</label>
                    <select
                      value={locPosDefaultMode}
                      onChange={(e) => setLocPosDefaultMode(e.target.value as any)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                    >
                      <option value="LOCAL">Local POS</option>
                      <option value="CLOUD">Cloud Replica POS</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="flex gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setLocationModalOpen(false)}
                  className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold py-2.5 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={locLoading || !locCode || !locName}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white text-xs font-semibold py-2.5 rounded-xl transition shadow-sm shadow-emerald-600/30"
                >
                  {locLoading ? "Saving..." : editingLocation ? "Update Location" : "Create Location"}
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
