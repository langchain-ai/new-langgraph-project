# VoicedForm - Voice-Powered Form Completion

A Next.js web application that enables users to create form templates and complete them using voice input or manual entry, with AI-powered validation and PDF generation.

## Features

### ✅ Implemented
- **Authentication**: Google OAuth sign-in with NextAuth.js
- **Dashboard**: View templates and recent form sessions
- **Template Management**: Create, edit, and delete form templates via API
- **Form Completion**: Progressive field-by-field completion interface
- **Review & Edit**: Inline editing of completed form values
- **PDF Generation**: Automatic PDF creation from form data
- **Email Delivery**: Send completed forms via email (placeholder implementation)

### 🚧 To Be Implemented
- **Template Editor UI**: Visual template builder (API exists, UI pending)
- **Voice Input**: Whisper WebSocket integration for speech-to-text
- **LLM Validation**: Smart field normalization and validation
- **Advanced Features**: Multi-language, analytics, collaboration

## Tech Stack

- **Frontend**: Next.js 14, React 19, TypeScript, Tailwind CSS
- **Backend**: Next.js API Routes
- **Database**: Supabase (Postgres)
- **Auth**: NextAuth.js with Google OAuth
- **PDF**: @react-pdf/renderer
- **Email**: Gmail API (placeholder)
- **Future**: OpenAI Whisper, OpenAI GPT-4

## Prerequisites

- Node.js 20+
- npm or pnpm
- Supabase account
- Google Cloud project (for OAuth)

## Setup Instructions

### 1. Install Dependencies

```bash
cd web
npm install
```

### 2. Set Up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Run the database schema from `/DESIGN.md` section 3.2 in the SQL editor
3. Enable Row Level Security and apply policies from section 3.3
4. Create a storage bucket named `form-pdfs` (optional, for PDF storage)
5. Copy your project URL and keys

### 3. Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized redirect URI: `http://localhost:3000/api/auth/callback/google`
6. Copy Client ID and Client Secret

### 4. Environment Variables

Create `.env.local` in the `web/` directory:

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your_random_32_char_secret # Generate with: openssl rand -base64 32

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_google_client_secret

# OpenAI (for future LLM features)
OPENAI_API_KEY=sk-your_openai_api_key

# Whisper (for future voice features)
WHISPER_WS_URL=ws://localhost:8765

# Gmail API (for email sending)
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
```

### 5. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Usage

### Creating a Template

Templates must currently be created via API or database directly. UI editor coming soon.

Example template structure:

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
          "constraints": { "required": true, "max_length": 100 },
          "hint": "Enter your first and last name"
        },
        {
          "label": "Email",
          "field_key": "email",
          "type": "string",
          "constraints": { "required": true },
          "hint": "Your email address"
        }
      ]
    }
  ]
}
```

Field types:
- `string`: Single-line text
- `paragraph`: Multi-line text
- `number`: Numeric input
- `date`: Date picker
- `enum`: Dropdown selection (requires `enum_values` in constraints)

### Completing a Form

1. Sign in with Google
2. From dashboard, click "Start Form" on any template
3. Fill out fields one by one
4. Review and edit if needed
5. Generate PDF and send via email

## Database Schema

See `/DESIGN.md` for complete schema. Key tables:

- `users`: User accounts
- `templates`: Form templates with JSON schema
- `form_sessions`: Form completion sessions
- `form_session_values`: Individual field values
- `pdf_documents`: Generated PDFs

## API Endpoints

### Authentication
- `GET /api/auth/signin` - Sign in
- `GET /api/auth/signout` - Sign out

### Templates
- `GET /api/templates` - List templates
- `POST /api/templates` - Create template
- `GET /api/templates/:id` - Get template
- `PUT /api/templates/:id` - Update template
- `DELETE /api/templates/:id` - Delete template

### Forms
- `POST /api/forms/create` - Start new session
- `GET /api/forms/:sessionId` - Get session details
- `POST /api/forms/:sessionId/update` - Save field value
- `POST /api/forms/:sessionId/complete` - Mark complete
- `POST /api/forms/:sessionId/pdf` - Generate PDF
- `POST /api/forms/:sessionId/email` - Send email

## Development

### Code Quality

```bash
# Lint
npm run lint

# Format
npm run format
```

### Building for Production

```bash
npm run build
npm start
```

## Deployment

### Vercel (Recommended)

1. Push code to GitHub
2. Import project in Vercel
3. Add environment variables
4. Deploy

### Other Platforms

Compatible with any Node.js hosting platform (Railway, Fly.io, AWS, etc.)

## Roadmap

- [ ] Template Editor UI
- [ ] Whisper voice input integration
- [ ] LLM-powered field validation
- [ ] Gmail OAuth flow for email sending
- [ ] Multi-language support
- [ ] Mobile responsiveness
- [ ] Form analytics
- [ ] Template marketplace
- [ ] Collaboration features

## Contributing

This is an MLP (Minimum Lovable Product). Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

MIT

## Support

For issues and questions, see `/REQ.md`, `/DESIGN.md`, and `/SPEC.md` for comprehensive documentation.
