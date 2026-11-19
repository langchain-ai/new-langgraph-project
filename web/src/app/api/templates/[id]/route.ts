import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase'
import { getCurrentUserId } from '@/lib/auth'
import { validateTemplateSchema } from '@/lib/validation'

// GET /api/templates/:id - Get template details
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const userId = await getCurrentUserId()
    const { id } = params

    const { data, error } = await supabaseAdmin
      .from('templates')
      .select('*')
      .eq('id', id)
      .eq('owner_user_id', userId)
      .is('deleted_at', null)
      .single()

    if (error || !data) {
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

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching template:', error)
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

// PUT /api/templates/:id - Update template
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const userId = await getCurrentUserId()
    const { id } = params
    const body = await request.json()

    // Verify ownership
    const { data: existing } = await supabaseAdmin
      .from('templates')
      .select('id')
      .eq('id', id)
      .eq('owner_user_id', userId)
      .is('deleted_at', null)
      .single()

    if (!existing) {
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

    // Validate schema if provided
    if (body.schema) {
      const validationResult = validateTemplateSchema(body.schema)
      if (!validationResult.valid) {
        return NextResponse.json(
          {
            error: {
              code: 'VALIDATION_ERROR',
              message: 'Invalid template schema',
              details: validationResult.errors,
            },
          },
          { status: 400 }
        )
      }
    }

    const updateData: any = {}
    if (body.name) updateData.name = body.name
    if (body.description !== undefined)
      updateData.description = body.description
    if (body.schema) updateData.schema = body.schema

    const { data, error } = await supabaseAdmin
      .from('templates')
      .update(updateData)
      .eq('id', id)
      .select()
      .single()

    if (error) throw error

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error updating template:', error)
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

// DELETE /api/templates/:id - Delete template (soft delete)
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const userId = await getCurrentUserId()
    const { id } = params

    // Verify ownership
    const { data: existing } = await supabaseAdmin
      .from('templates')
      .select('id')
      .eq('id', id)
      .eq('owner_user_id', userId)
      .is('deleted_at', null)
      .single()

    if (!existing) {
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

    // Check for active sessions
    const { data: activeSessions } = await supabaseAdmin
      .from('form_sessions')
      .select('id')
      .eq('template_id', id)
      .in('status', ['draft', 'in_progress'])
      .limit(1)

    if (activeSessions && activeSessions.length > 0) {
      return NextResponse.json(
        {
          error: {
            code: 'CONFLICT',
            message:
              'Cannot delete template with active form sessions. Complete or delete active sessions first.',
          },
        },
        { status: 409 }
      )
    }

    // Soft delete
    const { error } = await supabaseAdmin
      .from('templates')
      .update({ deleted_at: new Date().toISOString() })
      .eq('id', id)

    if (error) throw error

    return new NextResponse(null, { status: 204 })
  } catch (error) {
    console.error('Error deleting template:', error)
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
