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
  console_url?: string;
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

export type LocationStatus = "ACTIVE" | "ARCHIVED";
export type LocationApplicationStatus = "ACTIVE" | "DEACTIVATED";

export interface LocationApplication {
  id: string;
  organization_id: string;
  location_id: string;
  application_id: string;
  application_code?: string | null;
  application_name?: string | null;
  status: LocationApplicationStatus;
  activated_at: string;
  deactivated_at?: string | null;
}

export interface Location {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  description?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state_province?: string | null;
  postal_code?: string | null;
  country_code?: string | null;
  timezone: string;
  status: LocationStatus;
  metadata?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
  applications: LocationApplication[];
}

export interface LocationCreatePayload {
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
}

export interface LocationUpdatePayload {
  name?: string;
  description?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province?: string;
  postal_code?: string;
  country_code?: string;
  timezone?: string;
  status?: LocationStatus;
}


export type MainNavSection = 
  | "overview" 
  | "identity" 
  | "business_entities" 
  | "locations"
  | "org_members" 
  | "app_catalog" 
  | "subscriptions"
  | "security"
  | "audit"
  | "settings";
