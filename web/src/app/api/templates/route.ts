import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase'
import { getCurrentUserId } from '@/lib/auth'
import { validateTemplateSchema } from '@/lib/validation'

// GET /api/templates - List user's templates
export async function GET(request: NextRequest) {
  try {
    const userId = await getCurrentUserId()
    const { searchParams } = new URL(request.url)
    const limit = parseInt(searchParams.get('limit') || '20')
    const offset = parseInt(searchParams.get('offset') || '0')

    const { data, error } = await supabaseAdmin
      .from('templates')
      .select('*')
      .eq('owner_user_id', userId)
      .is('deleted_at', null)
      .order('updated_at', { ascending: false })
      .range(offset, offset + limit - 1)

    if (error) throw error

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching templates:', error)
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

// POST /api/templates - Create new template
export async function POST(request: NextRequest) {
  try {
    const userId = await getCurrentUserId()
    const body = await request.json()

    // Validate required fields
    if (!body.name || !body.schema) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Name and schema are required',
          },
        },
        { status: 400 }
      )
    }

    // Validate schema
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

    const { data, error } = await supabaseAdmin
      .from('templates')
      .insert({
        owner_user_id: userId,
        name: body.name,
        description: body.description || null,
        schema: body.schema,
      })
      .select()
      .single()

    if (error) throw error

    return NextResponse.json(data, { status: 201 })
  } catch (error) {
    console.error('Error creating template:', error)
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
