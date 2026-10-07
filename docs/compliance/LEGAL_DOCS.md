# Helix Intelligence — Legal Policies & Regulatory Compliance Dossier

> **STATUS: ENGINEERING PREVIEW DRAFT · NON-LAWYER COMPLIANCE BASELINE**  
> **OPERATOR**: Helix, operated by Ziad Sabry (Cairo, Egypt)  
> **CURRENT LIFECYCLE**: Pre-revenue Beta Preview  
> **CONTACT**: cultleaderzoz.dev@gmail.com / support@helix-intelligence.com  
> **APPLICABLE BASELINES**: EU/UK GDPR, California Consumer Privacy Act (CCPA/CPRA), Egypt Personal Data Protection Law (Law 151/2020), UAE Federal Decree-Law No. 45/2021, Saudi Arabia Personal Data Protection Law (PDPL).

---

## EXECUTIVE SUMMARY & OPEN LEGAL ITEMS

Before accepting commercial transactions, executing Stripe onboarding, or launching into broad un-gated public availability, qualified legal counsel must review and resolve the following open items:

1. **Entity Structure & Registered Corporate Name**:
   - *Current Implementation*: `"Helix, operated by Ziad Sabry"`, Cairo, Egypt.
   - *Action for Counsel*: Once incorporation is finalized (e.g. LLC / Sole Proprietorship under Egyptian law, Delaware C-Corp, or UK LTD), replace operator references with the formal corporate entity name, registered office address, and commercial registry number.
2. **Governing Law & Forum Selection**:
   - *Current Implementation*: Arab Republic of Egypt.
   - *Action for Counsel*: Advise on the optimal dispute resolution forum and arbitration clause (e.g. Cairo Regional Centre for International Commercial Arbitration — CRCICA, LCIA, or Delaware Chancery Court) considering our international B2B user base across North America, Europe, and MENA.
3. **Intellectual Property in AI-Generated Outputs & Public Ad Archives**:
   - *Current Implementation*:
     - User retains 100% ownership of their creative briefs, uploaded reference visual seeds, and output media generated via Create Studio.
     - Helix retains all rights to its proprietary algorithms, ranking heuristics, code, and aggregated benchmarks.
     - Third-party competitor advertisements from Meta Ad Library are used purely for comparative commentary and market research under fair use / fair dealing doctrines, with explicit attribution.
   - *Action for Counsel*: Confirm enforceability across EU copyright directive (Directive (EU) 2019/790 regarding Text and Data Mining exemptions) and US fair use principles.
4. **Cookie & Local Storage Exemption**:
   - *Verified via Technical Audit*: Helix loads **zero** third-party advertising cookies, **zero** behavioral pixels, and **zero** external font trackers.
   - *Storage*: Limited to `helix_access_token` (API session auth), `helix_cached_user` (tenant profile caching), and `theme` (UI preferences). Under the ePrivacy Directive and Egypt Law 151/2020, strictly necessary storage is exempt from consent banners.
5. **Refund & Commercial Billing Terms**:
   - *Current Status*: Platform is pre-revenue beta with free trial credits.
   - *Action for Counsel*: Draft the refund policy and payment dispute protocol when Stripe or LemonSqueezy payment processing is integrated.

---

# 1. Privacy Policy

**Last updated: October 2, 2026**

### 1.1 Who We Are
Helix ("we," "us," or "our") is an advertising intelligence, ad discovery, and creative analysis workstation operated by **Helix, operated by Ziad Sabry**, located in Cairo, Egypt. This Privacy Policy sets out how we collect, process, and protect your personal information when you access our web application, APIs, or marketing surfaces.

### 1.2 Data We Collect
We adhere strictly to data minimization principles. We only collect fields required to deliver the core service:
- **Account Identity**: Full name, work email address, and cryptographically salted/hashed passwords.
- **Workspace Usage Telemetry**: Search queries executed in Discover, ad creatives bookmarked or saved to Swipe Files, monitor alert configurations, credit consumption logs, and security telemetry (IP addresses and browser user-agent headers used exclusively for rate limiting and brute-force intrusion prevention).
- **User Provided Inputs**: Creative briefs, prompt configurations, uploaded reference image assets, and customer support ticket correspondence.
- **AI-Generated Outputs**: Teardown insights, modeled audience simulations, and creative renders generated in Create Studio, stored in association with your workspace ID.
- **Billing Details**: *Not collected during pre-revenue beta.* When commercial subscriptions launch, payment credentials will be processed directly by a PCI-DSS Level 1 certified payment gateway (e.g., Stripe); Helix never stores or processes raw credit card numbers.

### 1.3 Legal Bases for Processing
We process personal data under the following legal bases:
- **Contractual Performance**: To authenticate your account, fulfill search requests, and deliver platform features.
- **Legitimate Interests**: To monitor infrastructure health, safeguard against automated scraping or malicious attacks, and analyze aggregate, non-identifying performance metrics.
- **Consent**: Where you explicitly elect to opt in (e.g., optional product release announcement emails, freely revocable at any time).

### 1.4 Third-Party Sub-processors
Helix transfers data strictly to verified technical sub-processors bound by data processing agreements (DPAs):

| Sub-processor | Purpose | Location | Security Measures |
| :--- | :--- | :--- | :--- |
| **Neon Inc.** | Serverless PostgreSQL database hosting & storage | US / EU | SOC 2 Type II, AES-256 at rest, TLS 1.3 in transit |
| **Render Services Inc.** | Backend FastAPI application hosting & worker queues | US East | SOC 2 Type II, isolated VPC network containers |
| **Vercel Inc.** | Frontend SPA distribution and Edge CDN caching | Global Edge | SOC 2 Type II, ISO 27001 |
| **Cloudflare Inc.** | R2 zero-egress object storage for generated creatives | Global | SOC 2 Type II, encrypted bucket policies |
| **Groq Inc.** | Ultra low-latency LPU model inference for creative scoring | US | Zero-data-retention inference agreements |
| **OpenRouter / Google Gemini** | Multimodal LLM analysis & audience simulation | US / Global | Enterprise API agreements (no training on user data) |
| **Metapi & Adyntel** | Public ad library data aggregation & indexing | US / Global | Commercial public archive querying |
| **ScrapeGraphAI** | Competitor landing-page structure extraction | US / Global | Respects `robots.txt` and polite rate limits |
| **Higgsfield AI** | Premium generative motion and video rendering | US | Secure transient compute sandboxes |
| **Resend Inc.** | Transactional service notifications & password resets | US | SOC 2, DKIM/SPF/DMARC authenticated |

### 1.5 International Data Transfers
Personal data collected by Helix may be transferred to and maintained on cloud servers located outside your country of residence (predominantly the United States and European Union). When transferring data originating in the European Economic Area (EEA), United Kingdom, or Egypt, we rely on the European Commission's Standard Contractual Clauses (SCCs), UK International Data Transfer Agreements (IDTAs), and equivalent cross-border transfer authorizations mandated by the Egyptian Data Protection Centre under Law 151/2020.

### 1.6 User Rights
Under applicable global privacy regulations (GDPR, CCPA/CPRA, Egypt PDPL, UAE PDPL, Saudi PDPL), you have the right to:
1. **Access & Portability**: Request a copy of all personal information we maintain regarding your account in a machine-readable JSON format.
2. **Rectification**: Update or correct inaccurate personal details through Profile Settings.
3. **Erasure ("Right to be Forgotten")**: Request permanent deletion of your account and personal records. Records are permanently removed within 30 days of verified request.
4. **Restriction & Objection**: Object to the processing of your data for legitimate interest purposes or restrict processing during dispute resolutions.
5. **Withdraw Consent**: Revoke consent for optional marketing communications at any time with a single click.

To exercise any of these rights, email us directly at: `cultleaderzoz.dev@gmail.com`.

### 1.7 Data Retention Schedule
- **Active Accounts**: Retained for the duration of the active workspace subscription.
- **Account Closure**: Upon account termination, database records are queued for deletion and irreversibly purged within 30 calendar days.
- **Server Logs**: Ephemeral access logs (IP address, HTTP request path) are retained for 14 days solely for security auditing and volumetric attack mitigation before being rotated.

### 1.8 Children's Privacy
Helix Intelligence is strictly a B2B enterprise service. We do not knowingly market to or collect personal data from individuals under 16 years of age.

---

# 2. Terms of Service

**Last updated: October 2, 2026**

### 2.1 Acceptance of Agreement
By registering an account, invoking our APIs, or utilizing the Helix workstation, you agree to be bound by these Terms of Service. If you are entering into this agreement on behalf of a company, you represent that you possess the authority to bind that entity.

### 2.2 Scope of Service & Operational Disclaimers
Helix provides competitive advertising research, market archive indexing, pattern detection, and generative marketing assistance. You explicitly acknowledge:
1. **Ad Archive Provider Limitations**: Ad discovery records are indexed from public advertising repositories (including the Meta Ad Library). Public repositories have documented geographic, platform, and temporal limitations (e.g. Meta commercial transparency requirements skewed toward EU/UK records). Helix does not warrant that ad indices are exhaustive or real-time.
2. **AI-Generated Insights & Modeled Metrics**: All Deep Teardowns, ad fatigue warnings, and Audience Simulation reports are synthetic analytical models and statistical heuristics, not guarantees of actual marketplace performance. Audience simulations are creative rehearsal instruments, not customer behavioral guarantees.
3. **Attribution & Transparency**: Modeled metrics are explicitly labeled as synthetic or modeled across the application.

### 2.3 Acceptable Use Policy
You shall not:
- Reverse-engineer, decompile, or extract the underlying model weights, scoring algorithms, or source code of Helix.
- Use Helix to build or train a competing ad intelligence or creative generation product.
- Circumvent rate limits, workspace credit allotments, or role-based access controls.
- Generate or distribute defamatory, infringing, unlawful, or deceptive marketing creative assets.
- Misrepresent competitor ad campaigns or utilize generated creative assets to impersonate third-party brands.
- Share API authentication tokens across unauthorized external parties.

### 2.4 Intellectual Property Rights
- **Customer IP**: You retain full ownership and intellectual property rights in your creative briefs, uploaded reference media, and output creative files generated through the Create Studio, subject only to third-party rights in your source materials.
- **Helix IP**: Helix and its licensors retain exclusive ownership of the platform software, algorithmic logic, user interfaces, branding, and aggregated market benchmarks.
- **Third-Party Competitor Ad Assets**: All competitor advertisements, imagery, and trademarks indexed from public advertising repositories remain the intellectual property of their respective owners. Helix displays competitor ad records strictly for transformative, fair-use comparative commentary and research, with explicit advertiser page name and platform attribution.

### 2.5 Billing, Beta Credits, & Cancellation
- **Pre-revenue Beta**: During the beta preview, platform access is provided free or on pre-allocated trial credits. We reserve the right to modify credit rates or terminate abusive accounts.
- **Commercial General Availability**: Upon public commercial release, plan fees and billing cycles will be published on the pricing page.
- **Cancellation**: You may cancel or close your account at any time via Profile Settings.

### 2.6 Limitation of Liability & Warranty Disclaimer
HELIX IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED. TO THE MAXIMUM EXTENT PERMITTED UNDER APPLICABLE LAW:
- NEITHER HELIX NOR OPERATOR ZIAD SABRY SHALL BE LIABLE FOR ANY LOST PROFITS, LOSS OF ADVERTISING BUDGET, CORRUPTION OF DATA, OR CONSEQUENTIAL DAMAGES ARISING FROM RELIANCE ON IN-APP METRICS OR GENERATIVE INSIGHTS.
- OUR TOTAL AGGREGATE LIABILITY FOR ALL CLAIMS ARISING OUT OF THIS AGREEMENT IS STRICTLY LIMITED TO THE GREATER OF: (A) THE TOTAL AMOUNT PAID BY YOU TO HELIX IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM, OR (B) ONE HUNDRED US DOLLARS ($100 USD).

### 2.7 Governing Law & Jurisdiction
These Terms of Service shall be governed by and construed in accordance with the substantive laws of the Arab Republic of Egypt, without giving effect to conflict of law principles. Any dispute arising under or in connection with these Terms shall be resolved before the competent commercial courts in Cairo, Egypt.

---

# 3. Cookie & Local Storage Policy

**Last updated: October 2, 2026**

### 3.1 Zero Third-Party Advertising Trackers
Helix Intelligence does not utilize third-party marketing cookies, behavioral advertising trackers (e.g. Meta Pixel, TikTok Pixel, Google Ads tags), or cross-domain user tracking beacons.

### 3.2 Client-Side Storage Inventory
Our web application employs modern HTML5 `localStorage` strictly for technical authentication and operational preferences:

| Storage Key | Storage Mechanism | Purpose | Category | Expiration |
| :--- | :--- | :--- | :--- | :--- |
| `helix_access_token` | `localStorage` | Authenticates API requests to the backend with Bearer credentials | **Strictly Essential** | Persistent until logout |
| `helix_cached_user` | `localStorage` | Caches user profile and workspace permissions to eliminate UI layout reflow | **Strictly Essential** | Persistent until session clear |
| `theme` | `localStorage` | Preserves dark mode preference | Functional | Persistent |

### 3.3 Exemption from Cookie Banners
Under the European Union ePrivacy Directive (Directive 2002/58/EC), GDPR Article 6, and Egyptian Law 151/2020:
> Technologies used for the sole purpose of carrying out the transmission of a communication, or strictly necessary in order to provide an information society service explicitly requested by the subscriber or user, are exempt from consent requirements.

Because Helix uses only strictly necessary authentication storage and basic UI preferences, **an intrusive cookie tracking banner is not required**.

---

## 4. Contact & Compliance Inquiries

For legal notices, data subject requests, or security vulnerability disclosures:
- **Operator**: Helix, operated by Ziad Sabry
- **Address**: Cairo, Egypt
- **Direct Privacy Email**: `cultleaderzoz.dev@gmail.com`
- **General Support**: `support@helix-intelligence.com`
