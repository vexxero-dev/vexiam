# VEX IAM — Vexxero Identity & Access Management

> **One Identity. Multiple Organizations. Connected Applications.**  
> Centralized identity, organization management, authentication, authorization, subscriptions, and device access for the Vexxero ecosystem.

---

## Overview

VEX IAM is an API-first, multi-tenant identity and access management system built for the Vexxero suite of applications (Accounting ERP, POS, PMS, and future expansions). It provides:

- **Global Individual Accounts**: Each individual owns a single personal identity across all businesses.
- **Organization-Managed User Pools**: Businesses invite existing identities and manage their application access.
- **Decoupled Commercial Entitlements**: Subscriptions define purchased capacity (user seats, device seats, features), while application roles govern authorization.
- **Offline Device Licensing**: Hardware-bound Ed25519 asymmetric signed licenses with rolling offline grace periods for point-of-sale terminals.

---

## Core Architecture & Documentation

The full architectural proposal and technical specification is documented in:
- [VEX IAM Architecture Proposal & Technical Specification](file:///C:/Users/thenuka/.gemini/antigravity/brain/f86f4162-b22e-467f-9763-14953c9286b3/vex_iam_architecture_proposal.md)

### Technical Stack
- **Backend Framework**: Python FastAPI (Async)
- **Validation**: Pydantic v2
- **Database & ORM**: PostgreSQL 16 + SQLAlchemy 2.0 (Asyncpg) + Alembic
- **Identity & Tokens**: OAuth 2.1 / OIDC with Ed25519 token signatures & Argon2id password hashing
- **Cache & Revocation**: Redis 7+
- **Frontend Portals**: Next.js (Individual, Organization, and Platform Admin)
- **Licensing**: Ed25519 device-bound asymmetric license keys

---

## Implementation Roadmap

1. **Phase 1 — Identity Foundation**: User registration, email verification, Argon2id auth, sessions, and MFA.
2. **Phase 2 — Business Entities**: Organization lifecycle, atomic single-owner enforcement, invitations, and memberships.
3. **Phase 3 — Application Access**: Application registry (`VEX-ERP`, `VEX-POS`, `VEX-PMS`), permission mappings, and access assignments.
4. **Phase 4 — Subscriptions & Entitlements**: Individual & organization subscription plans, seat allocations, and billing webhooks.
5. **Phase 5 — Device Licensing**: Ed25519 device registration, offline license issuance, and 30-day rolling grace period sync.
6. **Phase 6 — Production Hardening**: Admin portals, rate limiting, audit logs, and security testing.
