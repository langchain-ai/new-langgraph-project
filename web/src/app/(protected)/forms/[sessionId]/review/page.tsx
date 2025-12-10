'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Button } from '@/components/shared/Button'
import type { FormSessionDetails, FormValue } from '@/types/database'

export default function ReviewPage() {
  const router = useRouter()
  const params = useParams()
  const sessionId = params.sessionId as string

  const [sessionData, setSessionData] = useState<FormSessionDetails | null>(
    null
  )
  const [editingField, setEditingField] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [recipientEmail, setRecipientEmail] = useState('')
  const [showEmailDialog, setShowEmailDialog] = useState(false)

  useEffect(() => {
    async function loadSession() {
      try {
        const response = await fetch(`/api/forms/${sessionId}`)
        if (!response.ok) throw new Error('Failed to load session')
        const data = await response.json()
        setSessionData(data)
      } catch (err) {
        alert((err as Error).message)
      } finally {
        setIsLoading(false)
      }
    }
    loadSession()
  }, [sessionId])

  const startEdit = (fieldKey: string, currentValue: string) => {
    setEditingField(fieldKey)
    setEditValue(currentValue)
  }

  const cancelEdit = () => {
    setEditingField(null)
    setEditValue('')
  }

  const saveEdit = async (fieldKey: string) => {
    try {
      await fetch(`/api/forms/${sessionId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          field_key: fieldKey,
          value_raw: editValue,
          value_normalized: editValue,
          validation_status: 'ok',
        }),
      })

      // Reload session data
      const response = await fetch(`/api/forms/${sessionId}`)
      const data = await response.json()
      setSessionData(data)
      setEditingField(null)
      setEditValue('')
    } catch (err) {
      alert('Failed to save changes')
    }
  }

  const generateAndSendPDF = async () => {
    if (!recipientEmail) {
      alert('Please enter a recipient email address')
      return
    }

    setIsGenerating(true)
    try {
      // Generate PDF
      const pdfResponse = await fetch(`/api/forms/${sessionId}/pdf`, {
        method: 'POST',
      })

      if (!pdfResponse.ok) throw new Error('Failed to generate PDF')
      const { pdf_url } = await pdfResponse.json()

      // Send email
      const emailResponse = await fetch(`/api/forms/${sessionId}/email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipient_email: recipientEmail,
          subject: `Form: ${sessionData?.template.name}`,
          pdf_url,
        }),
      })

      if (!emailResponse.ok) throw new Error('Failed to send email')

      alert('PDF generated and email sent successfully!')
      router.push('/dashboard')
    } catch (err) {
      alert((err as Error).message)
    } finally {
      setIsGenerating(false)
      setShowEmailDialog(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading...</p>
      </div>
    )
  }

  if (!sessionData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Session not found</p>
      </div>
    )
  }

  const valuesByKey = new Map(
    sessionData.values.map((v) => [v.field_key, v])
  )

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Review Form
          </h1>
          <p className="text-gray-600">{sessionData.template.name}</p>
        </div>

        {/* Form Values */}
        <div className="space-y-6">
          {sessionData.template.schema.sections.map((section, sIdx) => (
            <div key={sIdx} className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                {section.section_name}
              </h2>

              <div className="space-y-4">
                {section.fields.map((field) => {
                  const value = valuesByKey.get(field.field_key)
                  const isEditing = editingField === field.field_key

                  return (
                    <div
                      key={field.field_key}
                      className="border-b border-gray-200 pb-4 last:border-0"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <label className="font-medium text-gray-700">
                          {field.label}
                        </label>
                        {!isEditing && (
                          <button
                            onClick={() =>
                              startEdit(
                                field.field_key,
                                value?.value_normalized || ''
                              )
                            }
                            className="text-blue-600 hover:text-blue-800 text-sm"
                          >
                            Edit
                          </button>
                        )}
                      </div>

                      {isEditing ? (
                        <div className="space-y-2">
                          {field.type === 'paragraph' ? (
                            <textarea
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              className="w-full px-3 py-2 border rounded"
                              rows={4}
                            />
                          ) : (
                            <input
                              type={
                                field.type === 'number'
                                  ? 'number'
                                  : field.type === 'date'
                                    ? 'date'
                                    : 'text'
                              }
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              className="w-full px-3 py-2 border rounded"
                            />
                          )}
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              onClick={() => saveEdit(field.field_key)}
                            >
                              Save
                            </Button>
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={cancelEdit}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <p className="text-gray-900">
                          {value?.value_normalized || (
                            <span className="text-gray-400 italic">
                              No value
                            </span>
                          )}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="mt-8 flex gap-4">
          <Button
            onClick={() => setShowEmailDialog(true)}
            disabled={isGenerating}
            className="flex-1"
          >
            {isGenerating ? 'Processing...' : 'Generate PDF & Send Email'}
          </Button>
          <Button
            variant="secondary"
            onClick={() => router.push(`/forms/${sessionId}`)}
          >
            Back to Form
          </Button>
        </div>

        {/* Email Dialog */}
        {showEmailDialog && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
              <h3 className="text-lg font-semibold mb-4">Send Form via Email</h3>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  Recipient Email
                </label>
                <input
                  type="email"
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                  className="w-full px-3 py-2 border rounded"
                  placeholder="recipient@example.com"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={generateAndSendPDF} disabled={isGenerating}>
                  {isGenerating ? 'Sending...' : 'Send'}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => setShowEmailDialog(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
