import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase'
import { getCurrentUserId } from '@/lib/auth'
import { generateFormPDF } from '@/lib/pdf-generator'

// POST /api/forms/:sessionId/pdf - Generate PDF
export async function POST(
  request: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  try {
    const userId = await getCurrentUserId()
    const { sessionId } = params

    // Fetch session data
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

    // Fetch values
    const { data: values } = await supabaseAdmin
      .from('form_session_values')
      .select('*')
      .eq('session_id', sessionId)

    const sessionData = {
      session,
      template: session.template as any,
      values: values || [],
    }

    // Get user email for metadata
    const { data: user } = await supabaseAdmin
      .from('users')
      .select('email')
      .eq('id', userId)
      .single()

    // Generate PDF
    const pdfBuffer = await generateFormPDF(
      sessionData,
      user?.email || 'Unknown'
    )

    // Upload to Supabase Storage
    const fileName = `${sessionId}_${Date.now()}.pdf`
    const { data: uploadData, error: uploadError } = await supabaseAdmin.storage
      .from('form-pdfs')
      .upload(fileName, pdfBuffer, {
        contentType: 'application/pdf',
      })

    if (uploadError) {
      // If bucket doesn't exist, return a temporary solution
      console.error('Storage upload error:', uploadError)

      // For now, return a base64 encoded PDF that can be downloaded client-side
      const base64PDF = pdfBuffer.toString('base64')

      return NextResponse.json({
        pdf_url: `data:application/pdf;base64,${base64PDF}`,
        document_id: null,
        note: 'PDF generated but not stored. Configure Supabase Storage bucket "form-pdfs" for persistent storage.',
      })
    }

    // Get public URL
    const { data: urlData } = supabaseAdmin.storage
      .from('form-pdfs')
      .getPublicUrl(fileName)

    // Save PDF document record
    const { data: pdfDoc } = await supabaseAdmin
      .from('pdf_documents')
      .insert({
        session_id: sessionId,
        path_or_url: urlData.publicUrl,
        file_size_bytes: pdfBuffer.length,
      })
      .select()
      .single()

    return NextResponse.json({
      pdf_url: urlData.publicUrl,
      document_id: pdfDoc?.id,
    })
  } catch (error) {
    console.error('Error generating PDF:', error)
    return NextResponse.json(
      {
        error: { code: 'INTERNAL_ERROR', message: (error as Error).message },
      },
      { status: 500 }
    )
  }
}
