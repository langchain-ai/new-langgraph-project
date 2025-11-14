import { z } from 'zod'
import type { TemplateSchema } from '@/types/database'

const FieldConstraintsSchema = z.object({
  required: z.boolean().optional(),
  min_length: z.number().optional(),
  max_length: z.number().optional(),
  min: z.number().optional(),
  max: z.number().optional(),
  enum_values: z.array(z.string()).optional(),
  date_format: z.string().optional(),
})

const FieldSchema = z.object({
  label: z.string().min(1).max(100),
  field_key: z.string().regex(/^[a-z_][a-z0-9_]*$/),
  type: z.enum(['string', 'paragraph', 'number', 'date', 'enum']),
  constraints: FieldConstraintsSchema,
  hint: z.string().optional(),
})

const SectionSchema = z.object({
  section_name: z.string().min(1).max(100),
  fields: z.array(FieldSchema).min(1),
})

const TemplateSchemaValidator = z.object({
  sections: z.array(SectionSchema).min(1),
})

export function validateTemplateSchema(schema: any): {
  valid: boolean
  errors?: string[]
} {
  try {
    TemplateSchemaValidator.parse(schema)

    // Check for duplicate field_keys
    const fieldKeys = new Set<string>()
    for (const section of schema.sections) {
      for (const field of section.fields) {
        if (fieldKeys.has(field.field_key)) {
          return {
            valid: false,
            errors: [`Duplicate field_key: ${field.field_key}`],
          }
        }
        fieldKeys.add(field.field_key)
      }
    }

    // Validate enum fields have enum_values
    for (const section of schema.sections) {
      for (const field of section.fields) {
        if (field.type === 'enum' && !field.constraints.enum_values?.length) {
          return {
            valid: false,
            errors: [`Enum field '${field.field_key}' must have enum_values`],
          }
        }
      }
    }

    return { valid: true }
  } catch (error) {
    if (error instanceof z.ZodError) {
      return {
        valid: false,
        errors: error.errors.map((e) => `${e.path.join('.')}: ${e.message}`),
      }
    }
    return { valid: false, errors: [(error as Error).message] }
  }
}

export function isValidTemplateSchema(
  schema: any
): schema is TemplateSchema {
  return validateTemplateSchema(schema).valid
}
