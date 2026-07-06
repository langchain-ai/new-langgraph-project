import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase'
import { getCurrentUserId } from '@/lib/auth'
import { sendEmailWithAttachment } from '@/lib/gmail'

// POST /api/forms/:sessionId/email - Send PDF via email
export async function POST(
  request: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  try {
    const userId = await getCurrentUserId()
    const { sessionId } = params
    const body = await request.json()

    if (!body.recipient_email) {
      return NextResponse.json(
        {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'recipient_email is required',
          },
        },
        { status: 400 }
      )
    }

    // Verify session ownership
    const { data: session } = await supabaseAdmin
      .from('form_sessions')
      .select('*, template:templates(name, description)')
      .eq('id', sessionId)
      .eq('user_id', userId)
      .single()

    if (!session) {
      return NextResponse.json(
        { error: { code: 'NOT_FOUND', message: 'Session not found' } },
        { status: 404 }
      )
    }

    const template = session.template as any

    // Send email
    await sendEmailWithAttachment(
      body.recipient_email,
      body.subject || `Form: ${template.name}`,
      `
        <html>
          <body>
            <h2>${template.name}</h2>
            <p>${template.description || ''}</p>
            <p>Please find the completed form attached as a PDF.</p>
            <p>Generated: ${new Date().toLocaleString()}</p>
          </body>
        </html>
      `,
      body.pdf_url || ''
    )

    // Update session status to 'sent'
    await supabaseAdmin
      .from('form_sessions')
      .update({ status: 'sent' })
      .eq('id', sessionId)

    return NextResponse.json({
      success: true,
      message: 'Email sent successfully',
    })
  } catch (error) {
    console.error('Error sending email:', error)
    return NextResponse.json(
      {
        error: { code: 'INTERNAL_ERROR', message: (error as Error).message },
      },
      { status: 500 }
    )
  }
}
