// Database types matching Supabase schema

export interface User {
  id: string
  auth_provider_id: string
  email: string
  name: string | null
  avatar_url: string | null
  created_at: string
  updated_at: string
  last_login_at: string | null
}

export interface Template {
  id: string
  owner_user_id: string
  name: string
  description: string | null
  schema: TemplateSchema
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface TemplateSchema {
  sections: Section[]
}

export interface Section {
  section_name: string
  fields: Field[]
}

export type FieldType = 'string' | 'paragraph' | 'number' | 'date' | 'enum'

export interface Field {
  label: string
  field_key: string
  type: FieldType
  constraints: FieldConstraints
  hint?: string
}

export interface FieldConstraints {
  required?: boolean
  min_length?: number
  max_length?: number
  min?: number
  max?: number
  enum_values?: string[]
  date_format?: string
}

export type FormSessionStatus = 'draft' | 'in_progress' | 'completed' | 'sent'

export interface FormSession {
  id: string
  template_id: string
  user_id: string
  status: FormSessionStatus
  created_at: string
  updated_at: string
  completed_at: string | null
}

export type ValidationStatus = 'ok' | 'warning' | 'error'

export interface FormValue {
  id: string
  session_id: string
  field_key: string
  value_raw: string | null
  value_normalized: any
  validation_status: ValidationStatus
  validation_message: string | null
  created_at: string
  updated_at: string
}

export interface PDFDocument {
  id: string
  session_id: string
  path_or_url: string
  file_size_bytes: number | null
  created_at: string
}

// Extended types for UI

export interface TemplateWithStats extends Template {
  session_count?: number
}

export interface FormSessionWithTemplate extends FormSession {
  template?: Template
}

export interface FormSessionDetails {
  session: FormSession
  template: Template
  values: FormValue[]
}
