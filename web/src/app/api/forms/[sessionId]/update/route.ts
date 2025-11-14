import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase'
import { getCurrentUserId } from '@/lib/auth'

// POST /api/forms/:sessionId/update - Save field value
export async function POST(
  request: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  try {
    const userId = await getCurrentUserId()
    const { sessionId } = params
    const body = await request.json()

    // Verify session ownership
    const { data: session } = await supabaseAdmin
      .from('form_sessions')
      .select('id, user_id')
      .eq('id', sessionId)
      .eq('user_id', userId)
      .single()

    if (!session) {
      return NextResponse.json(
        { error: { code: 'NOT_FOUND', message: 'Session not found' } },
        { status: 404 }
      )
    }

    // Upsert field value
    const { data, error } = await supabaseAdmin
      .from('form_session_values')
      .upsert(
        {
          session_id: sessionId,
          field_key: body.field_key,
          value_raw: body.value_raw || null,
          value_normalized: body.value_normalized || null,
          validation_status: body.validation_status || 'ok',
          validation_message: body.validation_message || null,
        },
        { onConflict: 'session_id,field_key' }
      )
      .select()
      .single()

    if (error) throw error

    // Update session status to in_progress if it was draft
    await supabaseAdmin
      .from('form_sessions')
      .update({ status: 'in_progress' })
      .eq('id', sessionId)
      .eq('status', 'draft')

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error updating form value:', error)
    return NextResponse.json(
      {
        error: { code: 'INTERNAL_ERROR', message: (error as Error).message },
      },
      { status: 500 }
    )
  }
}
