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

export type MainNavSection = 
  | "overview" 
  | "identity" 
  | "business_entities" 
  | "org_members" 
  | "app_catalog" 
  | "subscriptions"
  | "security"
  | "audit"
  | "settings";
