export interface UserProfile {
  first_name: string;
  last_name: string;
}

export interface User {
  id: string;
  email: string;
  status: string;
  email_verified: boolean;
  profile?: UserProfile;
}

export interface Organization {
  id: string;
  name: string;
  registration_number?: string;
  status: string;
}

export interface Member {
  id: string;
  user_id: string;
  role: string;
  user?: User;
}

export interface Application {
  id: string;
  code: string;
  name: string;
  description?: string;
  type: string;
}

export interface Plan {
  id: string;
  application_id: string;
  code: string;
  name: string;
  description?: string;
  user_seats: number;
  device_seats: number;
}

export interface Subscription {
  id: string;
  plan_id: string;
  owner_type: string;
  organization_id?: string;
  status: string;
  expires_at?: string;
  created_at: string;
  plan?: Plan;
}

export interface DeviceLicenseSummary {
  id: string;
  application_id: string;
  status: string;
  expires_at: string;
  issued_at: string;
}

export interface Device {
  id: string;
  organization_id: string;
  location_id?: string | null;
  name: string;
  fingerprint: string;
  status: string;
  sync_enabled?: boolean;
  last_heartbeat_at?: string | null;
  menu_mode?: "LOCAL" | "CLOUD" | null;
  effective_menu_mode?: "LOCAL" | "CLOUD";
  licenses?: DeviceLicenseSummary[];
}

export interface OrgLocation {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  description?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country_code?: string;
  timezone?: string;
  status: string;
  metadata?: Record<string, any>;
  pos_sync_allowed?: boolean;
  pos_mode_policy?: "ANY_ALLOWED" | "LOCAL_ONLY" | "CLOUD_ONLY";
  pos_default_mode?: "LOCAL" | "CLOUD";
}

export interface ApplicationRole {
  id: string;
  application_id: string;
  code: string;
  name: string;
  description?: string;
}

export interface ApplicationAssignment {
  id: string;
  organization_id: string;
  user_id: string;
  application_id: string;
  status: string;
  created_at: string;
  roles: ApplicationRole[];
  application?: Application;
  user?: {
    id: string;
    email: string;
    profile?: {
      first_name: string;
      last_name: string;
    };
  };
}

export interface ActivatedSyncTicket {
  device_id: string;
  sync_endpoint: string;
  signed_ticket: string;
  signature_b64: string;
  expires_at: string;
}

export type MainNavSection = 
  | "overview" 
  | "identity" 
  | "business_entities" 
  | "app_catalog" 
  | "org_team" 
  | "org_locations" 
  | "org_terminals" 
  | "org_subscriptions"
  | "security"
  | "audit"
  | "settings";
