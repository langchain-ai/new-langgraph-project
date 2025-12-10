import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase'
import { getCurrentUserId } from '@/lib/auth'

// POST /api/forms/create - Start new form session
export async function POST(request: NextRequest) {
  try {
    const userId = await getCurrentUserId()
    const body = await request.json()

    if (!body.template_id) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'template_id is required',
          },
        },
        { status: 400 }
      )
    }

    // Verify template exists and user has access
    const { data: template } = await supabaseAdmin
      .from('templates')
      .select('id')
      .eq('id', body.template_id)
      .eq('owner_user_id', userId)
      .is('deleted_at', null)
      .single()

    if (!template) {
      return NextResponse.json(
        {
          error: {
            code: 'NOT_FOUND',
            message: 'Template not found',
          },
        },
        { status: 404 }
      )
    }

    // Create form session
    const { data, error } = await supabaseAdmin
      .from('form_sessions')
      .insert({
        template_id: body.template_id,
        user_id: userId,
        status: 'draft',
      })
      .select()
      .single()

    if (error) throw error

    return NextResponse.json(
      {
        session_id: data.id,
        redirect_url: `/forms/${data.id}`,
      },
      { status: 201 }
    )
  } catch (error) {
    console.error('Error creating form session:', error)
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
