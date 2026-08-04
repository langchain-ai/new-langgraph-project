import { google } from 'googleapis'

const OAuth2 = google.auth.OAuth2

export async function sendEmailWithAttachment(
  recipientEmail: string,
  subject: string,
  body: string,
  pdfUrl: string
): Promise<void> {
  try {
    // Create OAuth2 client
    const oauth2Client = new OAuth2(
      process.env.GMAIL_CLIENT_ID,
      process.env.GMAIL_CLIENT_SECRET,
      process.env.NEXTAUTH_URL + '/api/auth/callback/google'
    )

    // Note: In production, you would store and retrieve refresh tokens per user
    // For this MLP, we're using a simplified approach
    // You should implement proper OAuth flow to get user-specific tokens

    // For now, return a placeholder implementation
    // In production, you would:
    // 1. Get user's Gmail refresh token from database
    // 2. Set credentials on oauth2Client
    // 3. Create Gmail API client
    // 4. Fetch PDF from URL
    // 5. Create email with attachment
    // 6. Send email

    console.log('Email would be sent to:', recipientEmail)
    console.log('Subject:', subject)
    console.log('PDF URL:', pdfUrl)

    // Simulated success for MLP
    // TODO: Implement actual Gmail API integration
    return Promise.resolve()
  } catch (error) {
    console.error('Error sending email:', error)
    throw new Error('Failed to send email')
  }
}

// Helper to create email message with attachment
function createEmailMessage(
  to: string,
  subject: string,
  body: string,
  pdfBuffer: Buffer,
  fileName: string
): string {
  const boundary = '===============boundary==============='

  const message = [
    'MIME-Version: 1.0',
    `To: ${to}`,
    `Subject: ${subject}`,
    `Content-Type: multipart/mixed; boundary="${boundary}"`,
    '',
    `--${boundary}`,
    'Content-Type: text/html; charset=UTF-8',
    '',
    body,
    '',
    `--${boundary}`,
    'Content-Type: application/pdf',
    `Content-Disposition: attachment; filename="${fileName}"`,
    'Content-Transfer-Encoding: base64',
    '',
    pdfBuffer.toString('base64'),
    `--${boundary}--`,
  ].join('\r\n')

  return Buffer.from(message)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}
