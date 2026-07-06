# VoicedForm MLP - System Design Document

**Version:** 1.0
**Last Updated:** 2025-11-14
**Status:** Draft

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Browser)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │  React UI    │  │ WebSocket    │  │  Web Audio API     │   │
│  │  Components  │  │  Client      │  │  (Microphone)      │   │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬──────────┘   │
└─────────┼──────────────────┼────────────────────┼──────────────┘
          │                  │                    │
          │ HTTPS            │ WSS                │ Audio Chunks
          │                  │                    │
┌─────────▼──────────────────▼────────────────────▼──────────────┐
│                     Next.js Server                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              App Router (Pages + API Routes)            │   │
│  ├─────────────────┬───────────────────┬──────────────────┤   │
│  │  Auth Layer     │  Business Logic   │  WebSocket Server│   │
│  │  (NextAuth.js)  │  (Form/Template)  │  (ws/Socket.io)  │   │
│  └────────┬────────┴────────┬──────────┴─────────┬────────┘   │
└───────────┼─────────────────┼────────────────────┼────────────┘
            │                 │                    │
            │                 │                    │
    ┌───────▼──────┐  ┌──────▼──────────┐  ┌─────▼──────────┐
    │   Google     │  │   Supabase      │  │   Whisper      │
    │   OAuth      │  │   Postgres      │  │   Service      │
    │              │  │   + Storage     │  │   (Python)     │
    └──────────────┘  └────────┬────────┘  └────────────────┘
                               │
                        ┌──────▼──────┐
                        │   OpenAI    │
                        │   API       │
                        │   (LLM)     │
                        └─────────────┘
                               │
                        ┌──────▼──────┐
                        │   Gmail     │
                        │   API       │
                        └─────────────┘
```

### 1.2 Architecture Patterns

| Pattern | Implementation | Rationale |
|---------|----------------|-----------|
| **Monolithic Frontend** | Single Next.js application | Simplicity for MLP, easier deployment |
| **API Routes** | Next.js serverless functions | Built-in, no separate backend needed |
| **Real-time Communication** | WebSockets for audio streaming | Low latency for voice transcription |
| **Database-per-Service** | Single Postgres database | Simplified data consistency |
| **Stateless Services** | JWT-based sessions | Horizontal scalability |
| **Event-Driven** | WebSocket events for transcription | Reactive UI updates |

### 1.3 Component Responsibilities

#### **Next.js Application**
- Serve React frontend
- Handle authentication flow
- Manage template/form CRUD operations
- Proxy WebSocket connections to Whisper
- Generate PDFs
- Send emails via Gmail API
- Enforce access control

#### **Whisper Service**
- Accept WebSocket connections
- Receive audio chunks
- Perform speech-to-text transcription
- Return partial/final transcripts
- Handle multiple concurrent connections

#### **Supabase**
- Store user accounts
- Store templates and form sessions
- Store PDFs (via Storage)
- Enforce Row Level Security (RLS)
- Handle database migrations

#### **OpenAI API**
- LLM-based field normalization
- Ambiguity resolution
- Natural language date parsing

#### **Gmail API**
- Send emails with PDF attachments
- Manage OAuth tokens

---

## 2. Detailed Component Design

### 2.1 Frontend Architecture

```
app/
├── (public)/
│   ├── page.tsx                    # Landing page
│   └── layout.tsx                  # Public layout (no auth)
├── (protected)/
│   ├── dashboard/
│   │   └── page.tsx                # Dashboard
│   ├── templates/
│   │   ├── new/
│   │   │   └── page.tsx            # Create template
│   │   └── [id]/
│   │       └── page.tsx            # Edit template
│   ├── forms/
│   │   └── [sessionId]/
│   │       ├── page.tsx            # Voice completion
│   │       └── review/
│   │           └── page.tsx        # Review & edit
│   └── layout.tsx                  # Protected layout (auth check)
├── api/
│   ├── auth/
│   │   ├── [...nextauth]/
│   │   │   └── route.ts            # NextAuth config
│   │   └── callback/
│   │       └── route.ts            # OAuth callback
│   ├── templates/
│   │   ├── route.ts                # GET (list), POST (create)
│   │   └── [id]/
│   │       └── route.ts            # GET, PUT, DELETE
│   ├── forms/
│   │   ├── create/
│   │   │   └── route.ts            # POST (start session)
│   │   └── [sessionId]/
│   │       ├── route.ts            # GET (session details)
│   │       ├── update/
│   │       │   └── route.ts        # POST (save field)
│   │       ├── complete/
│   │       │   └── route.ts        # POST (mark complete)
│   │       ├── pdf/
│   │       │   └── route.ts        # POST (generate PDF)
│   │       └── email/
│   │           └── route.ts        # POST (send email)
│   └── transcribe/
│       └── route.ts                # WebSocket endpoint
├── components/
│   ├── auth/
│   │   └── SignInButton.tsx
│   ├── dashboard/
│   │   ├── TemplateCard.tsx
│   │   └── RecentSessions.tsx
│   ├── templates/
│   │   ├── TemplateEditor.tsx
│   │   ├── SectionEditor.tsx
│   │   └── FieldEditor.tsx
│   ├── forms/
│   │   ├── VoiceRecorder.tsx
│   │   ├── TranscriptDisplay.tsx
│   │   ├── FieldPrompt.tsx
│   │   ├── ProgressIndicator.tsx
│   │   └── NavigationControls.tsx
│   ├── review/
│   │   ├── FormReview.tsx
│   │   ├── EditableField.tsx
│   │   └── ValidationStatus.tsx
│   └── shared/
│       ├── Button.tsx
│       ├── Input.tsx
│       └── Modal.tsx
├── lib/
│   ├── supabase.ts                 # Supabase client
│   ├── openai.ts                   # OpenAI client
│   ├── gmail.ts                    # Gmail API wrapper
│   ├── validation.ts               # Field validation logic
│   ├── normalization.ts            # Value normalization
│   └── pdf-generator.ts            # PDF creation
├── types/
│   ├── template.ts
│   ├── form.ts
│   └── user.ts
└── middleware.ts                   # Auth middleware
```

### 2.2 Key React Components

#### VoiceRecorder Component
```typescript
interface VoiceRecorderProps {
  onTranscript: (text: string, isFinal: boolean) => void;
  onError: (error: Error) => void;
  fieldHint?: string;
}

// State:
// - isRecording: boolean
// - audioContext: AudioContext
// - mediaStream: MediaStream
// - websocket: WebSocket

// Methods:
// - startRecording(): Initialize mic, connect WebSocket
// - stopRecording(): Close connections, finalize transcript
// - sendAudioChunk(chunk: ArrayBuffer): Send to Whisper
```

#### TemplateEditor Component
```typescript
interface TemplateEditorProps {
  templateId?: string; // undefined for new template
}

// State:
// - template: Template
// - sections: Section[]
// - isDirty: boolean
// - validationErrors: ValidationError[]

// Methods:
// - addSection()
// - removeSection(id)
// - addField(sectionId)
// - updateField(sectionId, fieldId, updates)
// - saveTemplate()
// - validateSchema(): ValidationError[]
```

#### FormReview Component
```typescript
interface FormReviewProps {
  sessionId: string;
}

// State:
// - values: FormValue[]
// - editingFieldKey: string | null
// - isGenerating: boolean

// Methods:
// - editField(fieldKey)
// - saveFieldEdit(fieldKey, newValue)
// - generateAndSendPDF(recipientEmail)
```

### 2.3 Backend Services

#### Validation Service (`lib/validation.ts`)
```typescript
interface ValidationResult {
  isValid: boolean;
  normalizedValue: any;
  status: 'ok' | 'warning' | 'error';
  message?: string;
}

class FieldValidator {
  async validate(
    rawValue: string,
    fieldSchema: FieldSchema,
    context?: ValidationContext
  ): Promise<ValidationResult> {
    // 1. Deterministic validation by type
    // 2. Check constraints
    // 3. If ambiguous, call LLM
    // 4. Return result
  }

  private validateString(value: string, constraints: Constraints): ValidationResult
  private validateNumber(value: string, constraints: Constraints): ValidationResult
  private validateDate(value: string, constraints: Constraints): ValidationResult
  private validateEnum(value: string, constraints: Constraints): ValidationResult
  private async validateWithLLM(value: string, schema: FieldSchema): Promise<ValidationResult>
}
```

#### PDF Generator (`lib/pdf-generator.ts`)
```typescript
interface PDFOptions {
  sessionId: string;
  templateName: string;
  values: FormValue[];
  schema: TemplateSchema;
  generatedBy: string;
  generatedAt: Date;
}

async function generatePDF(options: PDFOptions): Promise<{
  path: string;
  sizeBytes: number;
}> {
  // Using @react-pdf/renderer:
  // 1. Create PDF document structure
  // 2. Render header with metadata
  // 3. Iterate sections and fields
  // 4. Style and format
  // 5. Save to storage
  // 6. Return path
}
```

#### Gmail Service (`lib/gmail.ts`)
```typescript
interface EmailOptions {
  to: string;
  subject: string;
  body: string;
  attachmentPath: string;
  attachmentName: string;
}

class GmailService {
  private oauthClient: OAuth2Client;

  async sendEmail(options: EmailOptions): Promise<void> {
    // 1. Get user's OAuth token
    // 2. Refresh if expired
    // 3. Create MIME message with attachment
    // 4. Send via Gmail API
    // 5. Handle errors/retry logic
  }

  async getAuthUrl(): string // For OAuth flow
  async handleCallback(code: string): Promise<Tokens>
}
```

### 2.4 Whisper Service Architecture

```python
# whisper_service.py
import asyncio
import websockets
import whisper
import numpy as np

class WhisperServer:
    def __init__(self, model_name='base.en'):
        self.model = whisper.load_model(model_name)
        self.connections = set()

    async def handle_connection(self, websocket, path):
        """Handle WebSocket connection from client."""
        self.connections.add(websocket)
        audio_buffer = []

        try:
            async for message in websocket:
                # Receive binary audio chunk
                audio_chunk = np.frombuffer(message, dtype=np.float32)
                audio_buffer.append(audio_chunk)

                # Every N chunks, send partial transcript
                if len(audio_buffer) >= 10:  # ~1 second of audio
                    audio = np.concatenate(audio_buffer)
                    result = self.model.transcribe(audio)
                    await websocket.send(json.dumps({
                        'type': 'partial',
                        'text': result['text']
                    }))

            # Connection closed, send final transcript
            if audio_buffer:
                audio = np.concatenate(audio_buffer)
                result = self.model.transcribe(audio)
                await websocket.send(json.dumps({
                    'type': 'final',
                    'text': result['text']
                }))

        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
        finally:
            self.connections.remove(websocket)

    def run(self, host='0.0.0.0', port=8765):
        start_server = websockets.serve(self.handle_connection, host, port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

if __name__ == '__main__':
    server = WhisperServer(model_name='base.en')
    server.run()
```

**Deployment:**
- Docker container with Python 3.10+
- Pre-loaded Whisper model in image
- Exposed on port 8765
- Environment variables: `WHISPER_MODEL`, `PORT`

---

## 3. Database Design

### 3.1 Entity-Relationship Diagram

```
┌──────────────┐
│    users     │
│──────────────│
│ id (PK)      │───┐
│ auth_prov... │   │
│ email        │   │
│ name         │   │
│ created_at   │   │
└──────────────┘   │
                   │
          ┌────────┴────────┐
          │                 │
┌─────────▼──────┐  ┌───────▼─────────┐
│   templates    │  │  form_sessions  │
│────────────────│  │─────────────────│
│ id (PK)        │◄─┤ id (PK)         │
│ owner_id (FK)  │  │ template_id (FK)│
│ name           │  │ user_id (FK)    │
│ schema (jsonb) │  │ status          │
│ created_at     │  │ created_at      │
└────────────────┘  └────────┬────────┘
                             │
                    ┌────────┴────────────┐
                    │                     │
        ┌───────────▼──────────┐  ┌───────▼────────┐
        │ form_session_values  │  │ pdf_documents  │
        │──────────────────────│  │────────────────│
        │ id (PK)              │  │ id (PK)        │
        │ session_id (FK)      │  │ session_id (FK)│
        │ field_key            │  │ path_or_url    │
        │ value_raw            │  │ file_size_bytes│
        │ value_normalized     │  │ created_at     │
        │ validation_status    │  └────────────────┘
        │ created_at           │
        └──────────────────────┘
```

### 3.2 Table Definitions (SQL)

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_provider_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_auth_provider ON users(auth_provider_id);

-- Templates table
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    schema JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT valid_schema CHECK (jsonb_typeof(schema) = 'object')
);

CREATE INDEX idx_templates_owner ON templates(owner_user_id);
CREATE INDEX idx_templates_deleted ON templates(deleted_at) WHERE deleted_at IS NULL;

-- Form sessions table
CREATE TABLE form_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    CONSTRAINT valid_status CHECK (status IN ('draft', 'in_progress', 'completed', 'sent'))
);

CREATE INDEX idx_sessions_user ON form_sessions(user_id);
CREATE INDEX idx_sessions_template ON form_sessions(template_id);
CREATE INDEX idx_sessions_status ON form_sessions(status);

-- Form session values table
CREATE TABLE form_session_values (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES form_sessions(id) ON DELETE CASCADE,
    field_key TEXT NOT NULL,
    value_raw TEXT,
    value_normalized JSONB,
    validation_status TEXT DEFAULT 'ok',
    validation_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_validation_status CHECK (validation_status IN ('ok', 'warning', 'error')),
    CONSTRAINT unique_session_field UNIQUE (session_id, field_key)
);

CREATE INDEX idx_values_session ON form_session_values(session_id);

-- PDF documents table
CREATE TABLE pdf_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES form_sessions(id) ON DELETE CASCADE,
    path_or_url TEXT NOT NULL,
    file_size_bytes INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pdfs_session ON pdf_documents(session_id);

-- Update timestamps trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON form_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_values_updated_at BEFORE UPDATE ON form_session_values
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 3.3 Row Level Security (RLS) Policies

```sql
-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE form_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE form_session_values ENABLE ROW LEVEL SECURITY;
ALTER TABLE pdf_documents ENABLE ROW LEVEL SECURITY;

-- Users: Can only read own record
CREATE POLICY users_read_own ON users
    FOR SELECT USING (auth.uid() = id);

-- Templates: Owner can do anything
CREATE POLICY templates_owner_all ON templates
    FOR ALL USING (owner_user_id = auth.uid());

-- Form sessions: User can manage own sessions
CREATE POLICY sessions_user_all ON form_sessions
    FOR ALL USING (user_id = auth.uid());

-- Form values: Can access if owns session
CREATE POLICY values_via_session ON form_session_values
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM form_sessions
            WHERE form_sessions.id = form_session_values.session_id
            AND form_sessions.user_id = auth.uid()
        )
    );

-- PDFs: Can access if owns session
CREATE POLICY pdfs_via_session ON pdf_documents
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM form_sessions
            WHERE form_sessions.id = pdf_documents.session_id
            AND form_sessions.user_id = auth.uid()
        )
    );
```

### 3.4 Sample Data

```sql
-- Insert sample user
INSERT INTO users (auth_provider_id, email, name) VALUES
    ('google_12345', 'john@example.com', 'John Doe');

-- Insert sample template
INSERT INTO templates (owner_user_id, name, description, schema) VALUES
    (
        (SELECT id FROM users WHERE email = 'john@example.com'),
        'Accident Report',
        'Template for workplace accident reporting',
        '{
            "sections": [
                {
                    "section_name": "Incident Details",
                    "fields": [
                        {
                            "label": "Date of Incident",
                            "field_key": "incident_date",
                            "type": "date",
                            "constraints": {"required": true},
                            "hint": "When did the incident occur?"
                        },
                        {
                            "label": "Description",
                            "field_key": "description",
                            "type": "paragraph",
                            "constraints": {"required": true, "min_length": 10},
                            "hint": "Describe what happened in detail"
                        }
                    ]
                }
            ]
        }'::jsonb
    );
```

---

## 4. Sequence Diagrams

### 4.1 Authentication Flow

```
User          Browser       Next.js      Google       Supabase
 │              │             │            │            │
 │──Click "Sign In"──>│       │            │            │
 │              │──GET /api/auth/signin──>│            │
 │              │             │──Redirect─>│            │
 │              │<─────OAuth Dialog────────│            │
 │──Authorize──>│             │            │            │
 │              │──────Auth Code────────> │            │
 │              │             │<─Tokens────│            │
 │              │             │──Create/Update User───>│
 │              │             │<────User Record────────│
 │              │<──Set Cookie + Redirect─│            │
 │              │──GET /dashboard──────> │             │
 │<─Dashboard──>│<────HTML───────────────│             │
```

### 4.2 Voice Form Completion Flow

```
Browser      Next.js     Whisper    OpenAI      Supabase
 │             │           │          │            │
 │──Start Recording──>    │           │            │
 │──Audio Chunks─────────────>        │            │
 │             │<──Partial Transcript─│            │
 │<─Display────│           │          │            │
 │──Stop Recording──>      │          │            │
 │             │<───Final Transcript──│            │
 │             │──Validate──>         │            │
 │             │──Is Ambiguous?       │            │
 │             │────Yes──────────────>│            │
 │             │<──Normalized Value───│            │
 │<─Show Value─│           │          │            │
 │──Accept─────>           │          │            │
 │             │──Save Field──────────────────────>│
 │             │<─────Success─────────────────────│
 │<─Next Field─│           │          │            │
```

### 4.3 PDF Generation & Email Flow

```
Browser      Next.js       Supabase    Gmail API    Storage
 │             │              │            │           │
 │──Click "Generate & Send"──>│            │           │
 │             │──Fetch Session Data─────>│            │
 │             │<───Values────│            │           │
 │             │──Generate PDF│            │           │
 │             │──Save PDF────────────────────────────>│
 │             │<──PDF URL────────────────────────────│
 │             │──Insert pdf_documents──>│            │
 │             │──Prepare Email──>        │            │
 │             │──Attach PDF──>           │            │
 │             │──────────────────────────>│           │
 │             │<──────Send Success───────│            │
 │             │──Update Session Status──>│            │
 │<─Success────│              │            │           │
```

### 4.4 Template Creation Flow

```
Browser      Next.js      Supabase
 │             │             │
 │──Fill Form─>│             │
 │──Add Sections/Fields───> │
 │──Click "Save"────────────>│
 │             │──Validate Schema
 │             │──INSERT INTO templates───>│
 │             │<────Template ID───────────│
 │<─Redirect to /dashboard──│              │
```

---

## 5. API Design

### 5.1 REST API Endpoints

#### Authentication
```
POST /api/auth/signin
  → Redirect to Google OAuth

GET /api/auth/callback?code=...
  ← 302 Redirect to /dashboard
  ← Set-Cookie: session_token

POST /api/auth/signout
  ← 200 OK
  ← Clear-Cookie
```

#### Templates
```
GET /api/templates?limit=20&offset=0
  ← 200 OK
  ← [{id, name, description, created_at, num_sessions}]

POST /api/templates
  ← 201 Created
  ← {id, name, description, schema, created_at}

GET /api/templates/:id
  ← 200 OK
  ← {id, name, description, schema, owner_user_id, created_at}

PUT /api/templates/:id
  ← 200 OK
  ← {id, name, description, schema, updated_at}

DELETE /api/templates/:id
  ← 204 No Content
```

#### Form Sessions
```
POST /api/forms/create
  Body: {template_id}
  ← 201 Created
  ← {session_id, redirect_url: "/forms/:session_id"}

GET /api/forms/:sessionId
  ← 200 OK
  ← {
      session: {id, status, created_at},
      template: {name, schema},
      values: [{field_key, value_normalized, validation_status}]
    }

POST /api/forms/:sessionId/update
  Body: {field_key, value_raw, value_normalized}
  ← 200 OK
  ← {validation_status, validation_message}

POST /api/forms/:sessionId/complete
  ← 200 OK
  ← {redirect_url: "/forms/:sessionId/review"}

POST /api/forms/:sessionId/pdf
  ← 201 Created
  ← {pdf_url, document_id}

POST /api/forms/:sessionId/email
  Body: {recipient_email, subject, message}
  ← 200 OK
  ← {sent: true}
```

### 5.2 WebSocket Protocol

**Endpoint:** `wss://app.voicedform.com/api/transcribe?session_id=...`

**Client → Server Messages:**
```json
// Binary audio chunk (ArrayBuffer)
[Float32Array audio data]
```

**Server → Client Messages:**
```json
// Partial transcript
{
  "type": "partial",
  "text": "This is a partial trans",
  "timestamp": "2025-11-14T10:30:00Z"
}

// Final transcript
{
  "type": "final",
  "text": "This is a partial transcript.",
  "confidence": 0.95,
  "timestamp": "2025-11-14T10:30:02Z"
}

// Error
{
  "type": "error",
  "message": "Transcription service unavailable",
  "code": "SERVICE_ERROR"
}
```

### 5.3 Error Response Format

All API errors follow this structure:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Template schema is invalid",
    "details": {
      "field": "schema.sections[0].fields[1].type",
      "issue": "Invalid field type 'textarea'. Must be one of: string, paragraph, number, date, enum"
    }
  }
}
```

**Standard Error Codes:**
- `AUTH_REQUIRED`: 401 Unauthorized
- `FORBIDDEN`: 403 Forbidden
- `NOT_FOUND`: 404 Not Found
- `VALIDATION_ERROR`: 400 Bad Request
- `CONFLICT`: 409 Conflict
- `INTERNAL_ERROR`: 500 Internal Server Error

---

## 6. Security Architecture

### 6.1 Authentication Flow

```
1. User clicks "Sign in with Google"
2. Next.js redirects to Google OAuth consent page
3. User authorizes application
4. Google redirects to /api/auth/callback with code
5. Next.js exchanges code for tokens
6. Next.js creates/updates user in Supabase
7. Next.js issues JWT session token (HTTP-only cookie)
8. Subsequent requests include cookie for auth
```

### 6.2 Authorization Model

| Resource | Rule |
|----------|------|
| Templates | User can only access own templates |
| Form Sessions | User can only access sessions they created |
| PDF Documents | User can only download PDFs for their sessions |
| Admin Routes | N/A (no admin for MLP) |

**Implementation:**
- Middleware checks session token on all `/dashboard`, `/templates`, `/forms` routes
- API routes validate user ID from token matches resource owner
- Supabase RLS enforces at database level

### 6.3 Data Protection

| Data Type | Protection |
|-----------|------------|
| Passwords | N/A (OAuth only) |
| Session Tokens | HTTP-only, Secure, SameSite=Lax cookies |
| API Keys (OpenAI, Gmail) | Environment variables, never sent to client |
| User Data | Encrypted at rest (Supabase default) |
| Audio Streams | TLS in transit, not persisted |
| PDFs | Supabase Storage with signed URLs (1-hour expiry) |

### 6.4 Threat Model & Mitigations

| Threat | Mitigation |
|--------|------------|
| XSS | React automatic escaping, CSP headers |
| CSRF | SameSite cookies, custom headers for mutations |
| SQL Injection | Parameterized queries via Supabase client |
| Auth Token Theft | HTTP-only cookies, short expiry (7 days) |
| Unauthorized Access | RLS policies, server-side auth checks |
| DDoS on Whisper | Rate limiting, WebSocket connection limits |
| Prompt Injection (LLM) | Input sanitization, system prompt hardening |

---

## 7. Performance Optimization

### 7.1 Frontend Optimizations

| Technique | Implementation |
|-----------|----------------|
| Code Splitting | Next.js automatic route-based splitting |
| Lazy Loading | `React.lazy()` for heavy components (PDF preview) |
| Image Optimization | Next.js `<Image>` component |
| Caching | `Cache-Control` headers for static assets |
| Prefetching | `<Link prefetch>` for dashboard navigation |

### 7.2 Backend Optimizations

| Technique | Implementation |
|-----------|----------------|
| Database Indexing | All foreign keys and frequently queried fields |
| Connection Pooling | Supabase handles automatically |
| Query Optimization | Select only needed columns, avoid N+1 queries |
| Caching | Redis for session data (future enhancement) |
| API Rate Limiting | `next-rate-limit` middleware |

### 7.3 Audio/Transcription Optimizations

| Technique | Implementation |
|-----------|----------------|
| Audio Compression | Use Opus codec if possible |
| Chunking | 1-second chunks to balance latency/accuracy |
| Model Selection | Use `tiny.en` for speed vs `base.en` for accuracy |
| Batching | Process multiple chunks together when possible |
| Connection Reuse | Keep WebSocket alive across fields |

### 7.4 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to Interactive (TTI) | <3s | Lighthouse |
| API Response Time (p95) | <500ms | Server logs |
| Transcription Latency (p95) | <1.5s | Client-side timing |
| LLM Validation (p95) | <3s | Server logs |
| PDF Generation | <5s | Server logs |
| Database Query (p95) | <100ms | Supabase dashboard |

---

## 8. Deployment Architecture

### 8.1 Hosting Plan

| Component | Platform | Rationale |
|-----------|----------|-----------|
| Next.js App | Vercel | Built for Next.js, easy deployment, edge functions |
| Supabase | Supabase Cloud | Managed Postgres + Storage, generous free tier |
| Whisper Service | Modal | Serverless GPU, WebSocket support, auto-scaling |
| OpenAI API | OpenAI Cloud | Pay-per-use |
| Gmail API | Google Cloud | Free within limits |

### 8.2 Environment Variables

**Next.js (.env.local):**
```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# NextAuth
NEXTAUTH_URL=https://app.voicedform.com
NEXTAUTH_SECRET=random_32_char_string

# Google OAuth
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx

# OpenAI
OPENAI_API_KEY=sk-xxx

# Gmail API
GMAIL_CLIENT_ID=xxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-xxx

# Whisper Service (Modal deployment)
WHISPER_WS_URL=wss://your-workspace--voicedform-whisper-transcribe-websocket.modal.run
```

**Note**: Whisper service is deployed to Modal. No additional environment variables needed for Whisper as configuration is handled in the Modal deployment script (`whisper-service/whisper_server.py`).

### 8.3 Deployment Pipeline

```
Developer          GitHub          Vercel         Production
    │                │               │                │
    │──git push───> │               │                │
    │                │──Webhook────>│                │
    │                │               │──Build Next.js │
    │                │               │──Run Tests     │
    │                │               │──Deploy Edge───>│
    │                │               │<──Success──────│
    │<───Notification────────────────│                │
```

**Whisper Service Deployment (Modal):**
```bash
# Install Modal CLI
pip install modal

# Authenticate with Modal
modal token new

# Deploy Whisper service
cd whisper-service
modal deploy whisper_server.py

# Get WebSocket endpoint URL from deployment output
# Example: wss://your-workspace--voicedform-whisper-transcribe-websocket.modal.run
```

See `/whisper-service/README.md` for detailed configuration, monitoring, and troubleshooting.

### 8.4 Monitoring & Logging

| Service | Tool | Metrics |
|---------|------|---------|
| Frontend | Vercel Analytics | Core Web Vitals, page views |
| Backend | Vercel Logs | API errors, response times |
| Database | Supabase Dashboard | Query performance, connection count |
| Whisper | Modal Dashboard & Logs | Transcription errors, latency, GPU usage, costs |
| Errors | Sentry (optional) | Exception tracking |

---

## 9. Data Flow Examples

### 9.1 Creating a Template

```
1. User fills out template form:
   - Name: "Accident Report"
   - Description: "Workplace accident reporting"
   - Adds section "Incident Details"
   - Adds fields: incident_date (date), description (paragraph)

2. User clicks "Save Template"

3. Browser sends POST /api/templates:
   {
     "name": "Accident Report",
     "description": "Workplace accident reporting",
     "schema": {
       "sections": [{
         "section_name": "Incident Details",
         "fields": [
           {
             "label": "Date of Incident",
             "field_key": "incident_date",
             "type": "date",
             "constraints": {"required": true},
             "hint": "When did it happen?"
           },
           {
             "label": "Description",
             "field_key": "description",
             "type": "paragraph",
             "constraints": {"required": true, "min_length": 20},
             "hint": "Describe what happened"
           }
         ]
       }]
     }
   }

4. API route validates schema:
   - All required fields present
   - Field types valid
   - No duplicate field_keys

5. API route inserts into Supabase:
   INSERT INTO templates (owner_user_id, name, description, schema)
   VALUES (current_user_id, 'Accident Report', '...', {...})

6. Returns 201 Created with template ID

7. Browser redirects to /dashboard
```

### 9.2 Completing a Form with Voice

```
1. User on /forms/abc-123 page
   - Current field: "Date of Incident" (type: date)
   - Hint displayed: "When did it happen?"

2. User clicks "Record" button

3. Browser captures microphone audio (Web Audio API)

4. Audio chunks sent via WebSocket to Whisper service:
   - Format: Float32Array, 16kHz sample rate
   - Chunk size: ~1 second

5. Whisper processes audio:
   - Partial transcripts sent every ~1 second:
     {"type": "partial", "text": "It happened on Nov"}

6. Browser displays partial transcript in real-time

7. User stops recording

8. Whisper sends final transcript:
   {"type": "final", "text": "It happened on November 10th"}

9. Next.js validates field:
   a. Extract value: "November 10th"
   b. Field type is "date"
   c. Parse natural language date → 2025-11-10
   d. Check constraints: required=true ✓
   e. Return normalized value

10. Browser shows:
    - Raw: "It happened on November 10th"
    - Normalized: "November 10, 2025"
    - Validation: ✓ OK

11. User clicks "Accept"

12. Browser sends POST /api/forms/abc-123/update:
    {
      "field_key": "incident_date",
      "value_raw": "It happened on November 10th",
      "value_normalized": "2025-11-10"
    }

13. API saves to form_session_values table

14. Browser progresses to next field: "Description"
```

### 9.3 Generating and Sending PDF

```
1. User completes all fields, on /forms/abc-123/review

2. User edits one field inline (fixes typo)
   - PATCH request updates form_session_values

3. User enters recipient email: "safety@company.com"

4. User clicks "Generate PDF & Send Email"

5. Browser sends POST /api/forms/abc-123/email:
   {
     "recipient_email": "safety@company.com",
     "subject": "Accident Report - November 10, 2025"
   }

6. API route:
   a. Fetch session data (template + values)
   b. Call PDF generator:
      - Render React PDF component
      - Layout sections and fields
      - Add metadata header
   c. Save PDF to Supabase Storage:
      - Bucket: "form-pdfs"
      - Path: "abc-123/report_20251114.pdf"
   d. Insert record in pdf_documents table
   e. Get signed URL (1-hour expiry)
   f. Call Gmail API:
      - Create MIME message
      - Attach PDF from signed URL
      - Send to recipient
   g. Update form_sessions.status = 'sent'

7. Return 200 OK

8. Browser shows success message, redirects to /dashboard
```

---

## 10. Error Handling Strategy

### 10.1 Frontend Error Boundaries

```typescript
// app/error.tsx (Global error boundary)
'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div>
      <h2>Something went wrong!</h2>
      <p>{error.message}</p>
      <button onClick={() => reset()}>Try again</button>
    </div>
  )
}
```

### 10.2 API Error Handling

```typescript
// lib/api-error.ts
export class APIError extends Error {
  constructor(
    public statusCode: number,
    public code: string,
    message: string,
    public details?: any
  ) {
    super(message)
  }

  toJSON() {
    return {
      error: {
        code: this.code,
        message: this.message,
        details: this.details,
      },
    }
  }
}

// Usage in API route:
if (!template) {
  throw new APIError(404, 'NOT_FOUND', 'Template not found')
}
```

### 10.3 Graceful Degradation

| Failure | Fallback |
|---------|----------|
| Whisper service down | Show manual text input field |
| LLM API timeout | Use deterministic validation only |
| Database connection lost | Retry 3x, then show maintenance page |
| PDF generation fails | Allow download as JSON |
| Email send fails | Save PDF, show download link |

---

## 11. Testing Strategy

### 11.1 Unit Tests
- Field validation logic (`lib/validation.ts`)
- Value normalization functions (`lib/normalization.ts`)
- Schema validation (`lib/template-schema.ts`)

### 11.2 Integration Tests
- API route handlers (templates, forms CRUD)
- Database operations
- OAuth flow (mocked)

### 11.3 End-to-End Tests (Future)
- Complete form workflow
- PDF generation
- Email sending (test mode)

### 11.4 Manual Testing Checklist
- [ ] Sign in with Google works
- [ ] Create template with all field types
- [ ] Start form session
- [ ] Record voice for each field type
- [ ] Transcript accuracy acceptable
- [ ] Normalization works for dates, numbers, enums
- [ ] Edit fields in review mode
- [ ] Generate PDF (verify formatting)
- [ ] Send email (verify receipt)
- [ ] Resume incomplete session

---

## 12. Future Enhancements

### 12.1 Phase 2 (Post-MLP)
- Multi-language support (Spanish, French)
- Mobile-responsive UI
- Voice output (TTS for confirmations)
- Collaborative forms (multiple users)
- Template versioning
- Advanced analytics dashboard
- Export formats (CSV, Excel)

### 12.2 Technical Debt to Address
- Add comprehensive test suite
- Implement caching layer (Redis)
- Set up staging environment
- Add performance monitoring (Datadog, New Relic)
- Implement request tracing
- Add database replication for HA
- Set up CDN for static assets

---

**Document Status:** Ready for Implementation
**Next Steps:** Create SPEC.md with task breakdown
