# VoicedForm MLP - Requirements Document

**Version:** 1.0
**Last Updated:** 2025-11-14
**Status:** Draft

---

## 1. Product Summary

### 1.1 Overview
VoicedForm is an **internal-only** web application that enables authenticated users to create form templates and complete them using voice input. The system provides real-time transcription, intelligent field validation, and automated PDF generation with email delivery.

### 1.2 Core Value Proposition
- **Voice-first form completion**: Hands-free data entry using natural language
- **Template-driven workflow**: Reusable form structures for recurring tasks
- **Intelligent validation**: Schema-based validation enhanced by LLM disambiguation
- **Automated delivery**: One-click PDF generation and Gmail distribution

### 1.3 Key Capabilities
1. Create and manage form templates
2. Complete forms using voice input with real-time transcription
3. Deterministic validation with LLM-assisted ambiguity resolution
4. Review and correct captured data
5. Generate formatted PDFs
6. Send completed forms via Gmail

### 1.4 Constraints
- **Internal use only**: No public access
- **English only**: Single language for MLP
- **Voice input only**: No voice output/TTS
- **Google authentication**: Single sign-on provider

---

## 2. User Roles & Access

### 2.1 Authenticated User
**Who:** Internal team members with Google accounts
**Access Level:** Full application access after OAuth
**Capabilities:**
- Create, edit, and delete own templates
- Start form sessions from any template
- Complete forms using voice input
- Review, edit, and submit forms
- Generate and send PDFs via email

### 2.2 Unauthenticated Visitor
**Who:** Anyone accessing the application URL
**Access Level:** Landing page only
**Capabilities:**
- View landing page
- Sign in with Google

---

## 3. Functional Requirements

### 3.1 Authentication (FR-AUTH)

#### FR-AUTH-001: Google OAuth Sign-In
- **Description:** Users must authenticate using Google OAuth 2.0
- **Flow:**
  1. User clicks "Sign in with Google" on landing page
  2. OAuth flow initiated with Google
  3. On success, user record created/updated in database
  4. Session token issued
  5. User redirected to /dashboard
- **Acceptance Criteria:**
  - First-time users create new user record
  - Returning users update last_login timestamp
  - Invalid/cancelled auth returns user to landing page with error

#### FR-AUTH-002: Session Management
- **Description:** Maintain user session across requests
- **Requirements:**
  - Session persists for 7 days
  - Auto-logout on expiry
  - Secure HTTP-only cookies
- **Acceptance Criteria:**
  - Protected routes redirect to landing if unauthenticated
  - Session renewal on active use

#### FR-AUTH-003: Logout
- **Description:** Users can manually sign out
- **Requirements:**
  - Clear session token
  - Redirect to landing page
- **Acceptance Criteria:**
  - All subsequent requests require re-authentication

### 3.2 Template Management (FR-TMPL)

#### FR-TMPL-001: Create Template
- **Description:** Users can create new form templates
- **Fields:**
  - Template name (required, max 100 chars)
  - Description (optional, max 500 chars)
  - Sections (array)
  - Fields (array)
- **Acceptance Criteria:**
  - Template saved to database with UUID
  - Owner set to current user
  - Timestamp recorded
  - Redirect to template editor on success

#### FR-TMPL-002: Template Schema Definition
- **Description:** Templates define structured form schemas
- **Field Properties:**
  - `label` (string): Display name
  - `field_key` (string): Unique identifier within template
  - `type` (enum): `string | paragraph | number | date | enum`
  - `constraints` (object): Validation rules
    - `required` (boolean)
    - `min_length` / `max_length` (number, for strings)
    - `min` / `max` (number, for numbers)
    - `enum_values` (array, for enum type)
    - `date_format` (string, for dates)
  - `hint` (string): User guidance text
- **Section Properties:**
  - `section_name` (string)
  - `fields` (array)
- **Acceptance Criteria:**
  - Schema stored as JSONB in Postgres
  - Schema validated on save
  - Duplicate field_keys rejected

#### FR-TMPL-003: Edit Template
- **Description:** Users can modify existing templates
- **Operations:**
  - Update name/description
  - Add/remove sections
  - Add/remove/reorder fields
  - Modify field constraints
- **Acceptance Criteria:**
  - Only owner can edit
  - Changes versioned (updated_at timestamp)
  - Active form sessions unaffected by template changes

#### FR-TMPL-004: Delete Template
- **Description:** Users can delete templates they own
- **Constraints:**
  - Cannot delete templates with active (draft/in_progress) sessions
  - Completed sessions remain in database
- **Acceptance Criteria:**
  - Confirmation dialog required
  - Soft delete (set deleted_at timestamp)
  - Removed from dashboard listing

#### FR-TMPL-005: List Templates
- **Description:** Dashboard displays user's templates
- **Display:**
  - Template name
  - Created date
  - Last modified date
  - Number of completed sessions
- **Sorting:**
  - Default: Most recently modified first
- **Acceptance Criteria:**
  - Only user's own templates shown
  - Deleted templates excluded

### 3.3 Voice-Driven Form Completion (FR-FORM)

#### FR-FORM-001: Create Form Session
- **Description:** User initiates form completion from template
- **Flow:**
  1. User selects template from dashboard
  2. System creates `form_session` record
  3. Status set to "draft"
  4. User redirected to `/forms/[sessionId]`
- **Acceptance Criteria:**
  - Session linked to template and user
  - Timestamp recorded
  - All template fields initialized

#### FR-FORM-002: Voice Recording
- **Description:** Capture audio from user microphone
- **Requirements:**
  - Browser-based audio capture using Web Audio API
  - Record in chunks (e.g., 1-second intervals)
  - Visual recording indicator (animated button)
  - Manual start/stop control
- **Acceptance Criteria:**
  - Audio format compatible with Whisper (WAV/PCM preferred)
  - Sample rate: 16kHz minimum
  - Recording can be stopped and restarted
  - No audio persisted to disk

#### FR-FORM-003: Real-Time Transcription
- **Description:** Convert speech to text using server-hosted Whisper
- **Architecture:**
  - WebSocket connection between browser and Whisper service
  - Streaming audio chunks sent to server
  - Partial/final transcripts returned
- **Requirements:**
  - Target latency: <1.5 seconds
  - English model (Tiny or Base)
  - Handle connection failures gracefully
- **Acceptance Criteria:**
  - Transcript displayed in real-time
  - Final transcript used for field population
  - Errors shown to user with retry option

#### FR-FORM-004: Field Normalization
- **Description:** Convert raw transcript to typed field value
- **Process:**
  1. Receive transcript from Whisper
  2. Extract field value based on type
  3. Apply normalization rules
  4. Validate against constraints
  5. Display normalized value to user
- **Type-Specific Normalization:**
  - **string**: Trim whitespace, capitalize if appropriate
  - **paragraph**: Preserve formatting, remove filler words
  - **number**: Extract numeric value, validate range
  - **date**: Parse natural language dates ("tomorrow", "next Friday")
  - **enum**: Match to closest allowed value
- **Acceptance Criteria:**
  - Normalized value matches field type
  - Invalid values flagged with warning
  - User can accept or re-record

#### FR-FORM-005: LLM-Assisted Disambiguation
- **Description:** Use LLM when deterministic parsing fails
- **Trigger Conditions:**
  - Multiple possible interpretations
  - Ambiguous date/time references
  - Unclear enum selection
  - Confidence score below threshold
- **Process:**
  1. Send to LLM with:
     - Field schema (type, constraints, hint)
     - Raw transcript
     - Context (previous fields if relevant)
  2. LLM returns:
     - Normalized value
     - Confidence score
     - Explanation
  3. Display to user for confirmation
- **Acceptance Criteria:**
  - LLM only invoked when needed (cost optimization)
  - User always has final approval
  - Explanation shown for transparency

#### FR-FORM-006: Field Navigation
- **Description:** Sequential progression through form fields
- **Controls:**
  - **Accept**: Save current value, advance to next field
  - **Back**: Return to previous field
  - **Re-record**: Discard current attempt, record again
  - **Manual Edit**: Type value instead of voice
- **Acceptance Criteria:**
  - Progress indicator shows position in form
  - Can navigate backward to correct mistakes
  - Current field highlighted
  - Section headers displayed for context

#### FR-FORM-007: Save Session State
- **Description:** Persist form progress incrementally
- **Requirements:**
  - Each accepted field saved to `form_session_values`
  - Session status updated (draft → in_progress)
  - Auto-save on field acceptance
- **Acceptance Criteria:**
  - User can close browser and resume later
  - Partial data not lost on disconnect
  - Last modified timestamp updated

#### FR-FORM-008: Complete Form Session
- **Description:** Mark all fields captured
- **Trigger:** User completes final field
- **Flow:**
  1. Validate all required fields populated
  2. Status changed to "completed"
  3. Redirect to `/forms/[sessionId]/review`
- **Acceptance Criteria:**
  - Cannot complete if required fields missing
  - Validation errors shown with field navigation

### 3.4 Review & Correction (FR-REVIEW)

#### FR-REVIEW-001: Display Completed Form
- **Description:** Show all captured values in structured view
- **Layout:**
  - Organized by sections
  - Field label + value pairs
  - Validation status indicators (✓/⚠/✗)
- **Acceptance Criteria:**
  - All fields visible
  - Warnings and errors highlighted
  - Read-only by default

#### FR-REVIEW-002: Inline Editing
- **Description:** Allow direct editing of field values
- **Interaction:**
  - Click field to enable edit mode
  - Type new value
  - Save or cancel
- **Validation:**
  - Re-validate on change
  - Show errors inline
  - Prevent save if validation fails
- **Acceptance Criteria:**
  - Edit updates `form_session_values`
  - Timestamp updated
  - Can edit any field

#### FR-REVIEW-003: Return to Voice Mode
- **Description:** Navigate back to voice completion from review
- **Requirements:**
  - Button to return to `/forms/[sessionId]`
  - Resume at last completed field
  - Status reverts to "in_progress"
- **Acceptance Criteria:**
  - No data lost
  - Can switch between modes freely

### 3.5 PDF Generation (FR-PDF)

#### FR-PDF-001: Generate PDF Document
- **Description:** Create formatted PDF from form data
- **Requirements:**
  - Use template schema for layout
  - Professional formatting:
    - Header with form name and date
    - Sections with clear headings
    - Field labels and values
    - Page numbers
  - Include metadata:
    - Generated by (user email)
    - Generated at (timestamp)
    - Template version
- **Library:** Use `pdfkit`, `puppeteer`, or `react-pdf`
- **Acceptance Criteria:**
  - PDF matches form structure
  - All values visible and readable
  - File size <5MB

#### FR-PDF-002: Store PDF
- **Description:** Persist generated PDF for reference
- **Storage Options:**
  - Supabase Storage (preferred)
  - Local filesystem
  - S3-compatible storage
- **Naming:** `{sessionId}_{timestamp}.pdf`
- **Acceptance Criteria:**
  - URL/path stored in `pdf_documents` table
  - PDF accessible for download
  - Record linked to session

### 3.6 Email Delivery (FR-EMAIL)

#### FR-EMAIL-001: Gmail OAuth Setup
- **Description:** Authenticate with Gmail API
- **Requirements:**
  - OAuth 2.0 flow for Gmail access
  - Scopes: `gmail.send`
  - Credentials stored securely server-side
- **Acceptance Criteria:**
  - User authorizes Gmail access once
  - Refresh tokens handled automatically
  - Revocation supported

#### FR-EMAIL-002: Send PDF via Email
- **Description:** Email generated PDF as attachment
- **Trigger:** User clicks "Generate PDF + Send Email" on review page
- **Email Content:**
  - **To:** Configurable recipient (user input or template default)
  - **From:** Authenticated user's Gmail
  - **Subject:** Template name + date
  - **Body:** Simple message with form summary
  - **Attachment:** Generated PDF
- **Acceptance Criteria:**
  - Email sent successfully
  - User receives confirmation
  - Session status set to "sent"
  - Error handling for delivery failures

#### FR-EMAIL-003: Email Confirmation
- **Description:** Show user confirmation before sending
- **Dialog Content:**
  - Recipient email
  - Subject line
  - Preview of attachment name
  - Send/Cancel buttons
- **Acceptance Criteria:**
  - No emails sent without explicit confirmation
  - User can edit recipient before send
  - Can download PDF without sending

---

## 4. Routes & Navigation

### 4.1 Route Map

| Route | Access | Description |
|-------|--------|-------------|
| `/` | Public | Landing page with sign-in |
| `/dashboard` | Protected | Template list and recent sessions |
| `/templates/new` | Protected | Create new template |
| `/templates/[id]` | Protected | Edit template |
| `/forms/[sessionId]` | Protected | Voice form completion |
| `/forms/[sessionId]/review` | Protected | Review and edit form |
| `/api/auth/callback` | Public | OAuth callback handler |
| `/api/templates` | Protected | Template CRUD endpoints |
| `/api/forms/*` | Protected | Form session endpoints |

### 4.2 Navigation Flow

```
Landing (/)
  ├─> Sign in with Google
  └─> Dashboard (/dashboard)
       ├─> Create Template
       │   └─> Template Editor (/templates/[id])
       │       └─> Back to Dashboard
       ├─> Start Form (select template)
       │   └─> Voice Completion (/forms/[sessionId])
       │       ├─> Review (/forms/[sessionId]/review)
       │       │   ├─> Edit inline
       │       │   ├─> Back to Voice Completion
       │       │   └─> Generate PDF + Send Email
       │       │       └─> Dashboard (on success)
       │       └─> Save & Exit → Dashboard
       └─> Resume Session (from recent list)
           └─> Voice Completion or Review (based on status)
```

---

## 5. Data Model

### 5.1 Database Schema

#### Table: `users`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | uuid | PRIMARY KEY | User identifier |
| `auth_provider_id` | text | UNIQUE NOT NULL | Google OAuth ID |
| `email` | text | UNIQUE NOT NULL | User email |
| `name` | text | | Display name |
| `avatar_url` | text | | Profile picture URL |
| `created_at` | timestamptz | DEFAULT NOW() | Account creation |
| `updated_at` | timestamptz | DEFAULT NOW() | Last update |
| `last_login_at` | timestamptz | | Last login timestamp |

#### Table: `templates`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | uuid | PRIMARY KEY | Template identifier |
| `owner_user_id` | uuid | FK → users.id | Template creator |
| `name` | text | NOT NULL | Template name |
| `description` | text | | Template description |
| `schema` | jsonb | NOT NULL | Form structure |
| `created_at` | timestamptz | DEFAULT NOW() | Creation timestamp |
| `updated_at` | timestamptz | DEFAULT NOW() | Last modification |
| `deleted_at` | timestamptz | | Soft delete timestamp |

**Schema JSONB Structure:**
```json
{
  "sections": [
    {
      "section_name": "Personal Information",
      "fields": [
        {
          "label": "Full Name",
          "field_key": "full_name",
          "type": "string",
          "constraints": {
            "required": true,
            "min_length": 2,
            "max_length": 100
          },
          "hint": "Speak your first and last name clearly"
        }
      ]
    }
  ]
}
```

#### Table: `form_sessions`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | uuid | PRIMARY KEY | Session identifier |
| `template_id` | uuid | FK → templates.id | Associated template |
| `user_id` | uuid | FK → users.id | Form completer |
| `status` | text | CHECK(...) | `draft | in_progress | completed | sent` |
| `created_at` | timestamptz | DEFAULT NOW() | Session start |
| `updated_at` | timestamptz | DEFAULT NOW() | Last activity |
| `completed_at` | timestamptz | | Completion timestamp |

#### Table: `form_session_values`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | uuid | PRIMARY KEY | Value identifier |
| `session_id` | uuid | FK → form_sessions.id | Parent session |
| `field_key` | text | NOT NULL | Field identifier from schema |
| `value_raw` | text | | Raw transcript |
| `value_normalized` | jsonb | | Typed value |
| `validation_status` | text | CHECK(...) | `ok | warning | error` |
| `validation_message` | text | | Error/warning details |
| `created_at` | timestamptz | DEFAULT NOW() | First capture |
| `updated_at` | timestamptz | DEFAULT NOW() | Last edit |

**UNIQUE CONSTRAINT:** `(session_id, field_key)`

#### Table: `pdf_documents`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | uuid | PRIMARY KEY | Document identifier |
| `session_id` | uuid | FK → form_sessions.id | Associated session |
| `path_or_url` | text | NOT NULL | Storage location |
| `file_size_bytes` | integer | | PDF file size |
| `created_at` | timestamptz | DEFAULT NOW() | Generation timestamp |

### 5.2 Database Indexes
- `users.auth_provider_id` (UNIQUE)
- `users.email` (UNIQUE)
- `templates.owner_user_id`
- `templates.deleted_at` (partial index WHERE deleted_at IS NULL)
- `form_sessions.user_id`
- `form_sessions.template_id`
- `form_sessions.status`
- `form_session_values.session_id`
- `pdf_documents.session_id`

---

## 6. API Endpoints

### 6.1 Authentication

#### `POST /api/auth/callback`
- **Description:** Handle OAuth callback from Google
- **Request Body:** Authorization code
- **Response:** Session token, redirect URL
- **Status Codes:** 200 (success), 401 (invalid code)

#### `POST /api/auth/logout`
- **Description:** End user session
- **Response:** Success confirmation
- **Status Codes:** 200

### 6.2 Templates

#### `GET /api/templates`
- **Description:** List user's templates
- **Query Params:** `limit`, `offset`
- **Response:** Array of templates
- **Status Codes:** 200, 401

#### `POST /api/templates`
- **Description:** Create new template
- **Request Body:** `{ name, description, schema }`
- **Response:** Created template with ID
- **Status Codes:** 201, 400 (validation error), 401

#### `GET /api/templates/[id]`
- **Description:** Get template details
- **Response:** Template object
- **Status Codes:** 200, 404, 403 (not owner)

#### `PUT /api/templates/[id]`
- **Description:** Update template
- **Request Body:** Updated fields
- **Response:** Updated template
- **Status Codes:** 200, 400, 404, 403

#### `DELETE /api/templates/[id]`
- **Description:** Delete template (soft delete)
- **Response:** Success confirmation
- **Status Codes:** 204, 404, 403, 409 (active sessions exist)

### 6.3 Form Sessions

#### `POST /api/forms/create`
- **Description:** Start new form session
- **Request Body:** `{ template_id }`
- **Response:** `{ session_id, redirect_url }`
- **Status Codes:** 201, 400, 404 (template not found)

#### `GET /api/forms/[sessionId]`
- **Description:** Get session details and current state
- **Response:** Session + values + template schema
- **Status Codes:** 200, 404, 403

#### `POST /api/forms/[sessionId]/update`
- **Description:** Save field value
- **Request Body:** `{ field_key, value_raw, value_normalized }`
- **Response:** Validation result
- **Status Codes:** 200, 400

#### `POST /api/forms/[sessionId]/complete`
- **Description:** Mark session as completed
- **Response:** Success confirmation
- **Status Codes:** 200, 400 (incomplete fields)

#### `POST /api/forms/[sessionId]/pdf`
- **Description:** Generate PDF
- **Response:** `{ pdf_url, document_id }`
- **Status Codes:** 201, 500 (generation failed)

#### `POST /api/forms/[sessionId]/email`
- **Description:** Send PDF via Gmail
- **Request Body:** `{ recipient_email, subject, message }`
- **Response:** Success confirmation
- **Status Codes:** 200, 400, 500 (send failed)

### 6.4 Whisper Transcription

#### `WebSocket /api/transcribe`
- **Description:** Streaming audio transcription
- **Messages:**
  - Client → Server: Binary audio chunks
  - Server → Client: `{ type: "partial" | "final", text: string }`
- **Connection:** Authenticated via query param or cookie

---

## 7. Non-Functional Requirements

### 7.1 Performance (NFR-PERF)

#### NFR-PERF-001: Transcription Latency
- **Requirement:** <1.5 seconds from speech end to transcript display
- **Measurement:** Client-side timestamp logging
- **Target:** 95th percentile

#### NFR-PERF-002: Validation Latency
- **Requirement:** <1 second for deterministic validation
- **Requirement:** <3 seconds for LLM-assisted validation
- **Target:** 95th percentile

#### NFR-PERF-003: Page Load Time
- **Requirement:** <2 seconds for initial page load (excluding OAuth)
- **Measurement:** Lighthouse performance score >90

#### NFR-PERF-004: PDF Generation
- **Requirement:** <5 seconds for forms with <50 fields
- **Requirement:** <10 seconds for larger forms

### 7.2 Security (NFR-SEC)

#### NFR-SEC-001: HTTPS Only
- **Requirement:** All traffic over TLS 1.2+
- **Enforcement:** HTTP → HTTPS redirect
- **HSTS:** Enabled with 1-year max-age

#### NFR-SEC-002: Secrets Management
- **Requirement:** All secrets server-side only
- **Implementation:**
  - Environment variables for API keys
  - No secrets in client-side code
  - Supabase Row Level Security (RLS) enabled

#### NFR-SEC-003: Authentication
- **Requirement:** All routes except `/` and `/api/auth/callback` require authentication
- **Session:** HTTP-only, secure, SameSite=Lax cookies
- **Expiry:** 7 days with sliding window

#### NFR-SEC-004: Data Privacy
- **Requirement:** No raw audio stored on server
- **Requirement:** Transcripts stored only in database
- **Requirement:** PDFs accessible only to session owner

#### NFR-SEC-005: Input Validation
- **Requirement:** All user inputs sanitized
- **Protection:** XSS prevention, SQL injection prevention (via ORM)

### 7.3 Observability (NFR-OBS)

#### NFR-OBS-001: Structured Logging
- **Requirement:** JSON-formatted logs
- **Fields:**
  - `timestamp`
  - `level` (info, warn, error)
  - `event_type` (auth, template_create, session_start, etc.)
  - `user_id`
  - `session_id`
  - `duration_ms` (for operations)
  - `error_message` (if applicable)

#### NFR-OBS-002: Session Tracing
- **Requirement:** Group all logs for a session under single trace ID
- **Implementation:** Pass `session_id` through all operations

#### NFR-OBS-003: Error Tracking
- **Requirement:** Client-side errors reported to server
- **Implementation:** Global error boundary in React
- **Capture:**
  - Error message
  - Stack trace
  - User context
  - Browser/OS info

### 7.4 Reliability (NFR-REL)

#### NFR-REL-001: Auto-Save
- **Requirement:** Form progress saved on every field acceptance
- **Recovery:** Users can resume sessions after browser close

#### NFR-REL-002: Graceful Degradation
- **Requirement:** If Whisper service unavailable, allow manual text input
- **Requirement:** If LLM service unavailable, fall back to deterministic validation only

#### NFR-REL-003: Database Backups
- **Requirement:** Daily automated backups
- **Retention:** 30 days
- **Recovery:** RPO <24 hours, RTO <4 hours

### 7.5 Usability (NFR-UX)

#### NFR-UX-001: Keyboard Navigation
- **Requirement:** All functions accessible via keyboard
- **Shortcuts:**
  - `Space` or `R`: Start/stop recording
  - `Enter`: Accept field
  - `Backspace`: Go back
  - `E`: Edit field manually

#### NFR-UX-002: Accessibility
- **Requirement:** WCAG 2.1 Level AA compliance
- **Implementation:**
  - Semantic HTML
  - ARIA labels
  - Sufficient color contrast (4.5:1 minimum)
  - Focus indicators

#### NFR-UX-003: Responsive Design
- **Requirement:** Functional on desktop (1920x1080) and tablet (1024x768)
- **Note:** Mobile support deferred (keyboard requirement)

#### NFR-UX-004: Error Messages
- **Requirement:** User-friendly error messages
- **Format:**
  - Clear description of problem
  - Suggested action
  - No technical jargon

---

## 8. Technology Stack

### 8.1 Frontend
- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript 5+
- **UI Library:** React 19
- **Styling:** Tailwind CSS (or CSS Modules)
- **State Management:** React Context + hooks
- **Audio Capture:** Web Audio API
- **WebSocket Client:** Native WebSocket or Socket.io-client

### 8.2 Backend
- **Runtime:** Node.js 20+
- **API Framework:** Next.js API Routes
- **Database:** Supabase Postgres
- **ORM:** Supabase JS Client
- **Authentication:** NextAuth.js with Google provider
- **WebSocket Server:** ws or Socket.io

### 8.3 AI/ML Services
- **Transcription:** OpenAI Whisper (self-hosted)
  - Model: `tiny.en` or `base.en`
  - Deployment: Docker container or Python service
- **LLM:** OpenAI GPT-4 or GPT-3.5-turbo
  - SDK: `openai` npm package

### 8.4 External Services
- **Email:** Gmail API
- **PDF Generation:** `@react-pdf/renderer` or `puppeteer`
- **File Storage:** Supabase Storage

### 8.5 Development Tools
- **Package Manager:** npm or pnpm
- **Linting:** ESLint
- **Formatting:** Prettier
- **Type Checking:** TypeScript strict mode
- **Testing:** Jest + React Testing Library (optional for MLP)

---

## 9. Out of Scope

The following are explicitly excluded from the MLP:

### 9.1 Features
- Public access / registration
- Multi-tenant architecture
- Role-based access control (admin/user roles)
- Collaboration (multiple users on same form)
- Form versioning
- Template marketplace
- Mobile app
- Voice output / text-to-speech
- Multi-language support
- Form analytics / reporting
- Integration with external systems (Salesforce, etc.)
- Offline mode
- Real-time collaboration

### 9.2 Technical
- Microservices architecture
- Kubernetes deployment
- Load balancing
- CDN integration
- Advanced caching strategies
- A/B testing framework
- Comprehensive test suite (unit/integration/e2e)

---

## 10. Success Criteria

The MLP is considered successful when:

### 10.1 Functional Completeness
- [ ] User can sign in with Google
- [ ] User can create a template with 10+ fields across 3 sections
- [ ] User can start a form session
- [ ] User can complete entire form using voice only
- [ ] Transcription accuracy >85% (English, clear speech)
- [ ] User can review and edit captured data
- [ ] PDF generated matches form structure
- [ ] PDF sent via Gmail successfully
- [ ] User can resume incomplete sessions

### 10.2 Performance
- [ ] Transcription latency <1.5s (p95)
- [ ] Page load <2s (p95)
- [ ] No blocking UI during transcription

### 10.3 Reliability
- [ ] Zero data loss during session (auto-save works)
- [ ] Graceful handling of Whisper service downtime
- [ ] Database constraints prevent invalid data

### 10.4 Usability
- [ ] Non-technical user can create template without guidance
- [ ] Non-technical user can complete form without guidance
- [ ] Error messages are clear and actionable

---

## 11. Assumptions & Dependencies

### 11.1 Assumptions
- Users have modern browsers (Chrome/Firefox/Safari latest versions)
- Users have working microphones
- Users have Google accounts
- Network latency <100ms to server
- Users speak clearly in English
- Forms typically <100 fields

### 11.2 Dependencies
- Google OAuth API availability
- OpenAI API availability (for LLM)
- Gmail API availability
- Supabase service uptime
- Whisper model availability

### 11.3 Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Whisper transcription accuracy low | High | Provide manual edit fallback |
| LLM API costs exceed budget | Medium | Implement aggressive caching, limit calls |
| Gmail API rate limits | Medium | Queue emails, implement retry logic |
| Browser audio API incompatibility | High | Feature detection, graceful degradation |
| Database performance degradation | Medium | Proper indexing, query optimization |

---

## 12. Acceptance Testing Scenarios

### Scenario 1: First-Time User Journey
1. User navigates to landing page
2. Clicks "Sign in with Google"
3. Authorizes application
4. Lands on empty dashboard
5. Clicks "Create Template"
6. Adds template name "Incident Report"
7. Adds section "Details"
8. Adds 5 fields (string, paragraph, date, number, enum)
9. Saves template
10. Returns to dashboard (template visible)

**Pass Criteria:** Template appears in list, all fields saved correctly

### Scenario 2: Voice Form Completion
1. User selects template from dashboard
2. Clicks "Start New Form"
3. Sees first field prompt
4. Clicks record button
5. Speaks field value
6. Sees transcript appear
7. Sees normalized value
8. Clicks "Accept"
9. Progresses to next field
10. Completes all fields
11. Redirected to review page

**Pass Criteria:** All spoken values captured, transcript matches speech, no crashes

### Scenario 3: Edit and Submit
1. User on review page
2. Notices error in field 3
3. Clicks field to edit
4. Types correction
5. Saves edit
6. Clicks "Generate PDF + Send Email"
7. Confirms recipient email
8. Clicks "Send"
9. Sees success message
10. Receives email with PDF

**Pass Criteria:** Edit saved, PDF contains corrected value, email delivered

---

## Appendices

### Appendix A: Glossary
- **MLP:** Minimum Lovable Product
- **OAuth:** Open Authorization
- **Whisper:** OpenAI's speech recognition model
- **LLM:** Large Language Model
- **RLS:** Row Level Security (Supabase feature)
- **TTS:** Text-to-Speech
- **WCAG:** Web Content Accessibility Guidelines

### Appendix B: References
- [Next.js Documentation](https://nextjs.org/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [Gmail API](https://developers.google.com/gmail/api)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

---

**Document Status:** Ready for Design Phase
**Next Steps:** Create DESIGN.md and SPEC.md
