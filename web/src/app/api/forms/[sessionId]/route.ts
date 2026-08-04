import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase'
import { getCurrentUserId } from '@/lib/auth'

// GET /api/forms/:sessionId - Get session details
export async function GET(
  request: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  try {
    const userId = await getCurrentUserId()
    const { sessionId } = params

    // Fetch session
    const { data: session, error: sessionError } = await supabaseAdmin
      .from('form_sessions')
      .select('*')
      .eq('id', sessionId)
      .eq('user_id', userId)
      .single()

    if (sessionError || !session) {
      return NextResponse.json(
        {
          error: {
            code: 'NOT_FOUND',
            message: 'Form session not found',
          },
        },
        { status: 404 }
      )
    }

    // Fetch template
    const { data: template } = await supabaseAdmin
      .from('templates')
      .select('*')
      .eq('id', session.template_id)
      .single()

    // Fetch values
    const { data: values } = await supabaseAdmin
      .from('form_session_values')
      .select('*')
      .eq('session_id', sessionId)
      .order('created_at', { ascending: true })

    return NextResponse.json({
      session,
      template,
      values: values || [],
    })
  } catch (error) {
    console.error('Error fetching form session:', error)
    return NextResponse.json(
      {
        error: {
          code: 'INTERNAL_ERROR',
          message: (error as Error).message,
        },
      },
      { status: 500 }
    )
  }
}
