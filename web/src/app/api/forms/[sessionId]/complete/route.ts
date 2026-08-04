import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase'
import { getCurrentUserId } from '@/lib/auth'

// POST /api/forms/:sessionId/complete - Mark session as completed
export async function POST(
  request: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  try {
    const userId = await getCurrentUserId()
    const { sessionId } = params

    // Verify session ownership
    const { data: session } = await supabaseAdmin
      .from('form_sessions')
      .select('*, template:templates(*)')
      .eq('id', sessionId)
      .eq('user_id', userId)
      .single()

    if (!session) {
      return NextResponse.json(
        { error: { code: 'NOT_FOUND', message: 'Session not found' } },
        { status: 404 }
      )
    }

    // Get all field values
    const { data: values } = await supabaseAdmin
      .from('form_session_values')
      .select('*')
      .eq('session_id', sessionId)

    // Check if all required fields are filled
    const template = session.template as any
    const requiredFields: string[] = []

    template.schema.sections.forEach((section: any) => {
      section.fields.forEach((field: any) => {
        if (field.constraints?.required) {
          requiredFields.push(field.field_key)
        }
      })
    })

    const filledFields = new Set(
      values?.map((v) => v.field_key) || []
    )
    const missingFields = requiredFields.filter(
      (key) => !filledFields.has(key)
    )

    if (missingFields.length > 0) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Required fields missing',
            details: { missing_fields: missingFields },
          },
        },
        { status: 400 }
      )
    }

    // Update session status
    const { data, error } = await supabaseAdmin
      .from('form_sessions')
      .update({
        status: 'completed',
        completed_at: new Date().toISOString(),
      })
      .eq('id', sessionId)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error completing form session:', error)
    return NextResponse.json(
      {
        error: { code: 'INTERNAL_ERROR', message: (error as Error).message },
      },
      { status: 500 }
    )
  }
}
