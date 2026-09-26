'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Button } from '@/components/shared/Button'
import { Input } from '@/components/shared/Input'
import type { FormSessionDetails, Field } from '@/types/database'

export default function FormCompletionPage() {
  const router = useRouter()
  const params = useParams()
  const sessionId = params.sessionId as string

  const [sessionData, setSessionData] = useState<FormSessionDetails | null>(
    null
  )
  const [currentFieldIndex, setCurrentFieldIndex] = useState(0)
  const [currentValue, setCurrentValue] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Get all fields in order
  const allFields: (Field & { sectionName: string })[] =
    sessionData?.template.schema.sections.flatMap((section) =>
      section.fields.map((field) => ({
        ...field,
        sectionName: section.section_name,
      }))
    ) || []

  const currentField = allFields[currentFieldIndex]
  const progress = ((currentFieldIndex + 1) / allFields.length) * 100

  // Load session data
  useEffect(() => {
    async function loadSession() {
      try {
        const response = await fetch(`/api/forms/${sessionId}`)
        if (!response.ok) throw new Error('Failed to load session')
        const data = await response.json()
        setSessionData(data)

        // Find the first unfilled field
        const filledKeys = new Set(data.values.map((v: any) => v.field_key))
        const firstUnfilledIndex = allFields.findIndex(
          (f) => !filledKeys.has(f.field_key)
        )
        setCurrentFieldIndex(
          firstUnfilledIndex >= 0 ? firstUnfilledIndex : 0
        )
      } catch (err) {
        setError((err as Error).message)
      } finally {
        setIsLoading(false)
      }
    }
    loadSession()
  }, [sessionId])

  const saveField = async () => {
    if (!currentValue.trim()) {
      if (currentField.constraints?.required) {
        alert('This field is required')
        return
      }
    }

    setIsSaving(true)
    try {
      await fetch(`/api/forms/${sessionId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          field_key: currentField.field_key,
          value_raw: currentValue,
          value_normalized: currentValue,
          validation_status: 'ok',
        }),
      })

      // Move to next field or complete
      if (currentFieldIndex < allFields.length - 1) {
        setCurrentFieldIndex(currentFieldIndex + 1)
        setCurrentValue('')
      } else {
        // Complete the session
        await fetch(`/api/forms/${sessionId}/complete`, {
          method: 'POST',
        })
        router.push(`/forms/${sessionId}/review`)
      }
    } catch (err) {
      alert('Failed to save field')
    } finally {
      setIsSaving(false)
    }
  }

  const goBack = () => {
    if (currentFieldIndex > 0) {
      setCurrentFieldIndex(currentFieldIndex - 1)
      setCurrentValue('')
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading form...</p>
      </div>
    )
  }

  if (error || !sessionData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || 'Session not found'}</p>
          <Button onClick={() => router.push('/dashboard')}>
            Back to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {sessionData.template.name}
          </h1>
          <p className="text-gray-600">{sessionData.template.description}</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>
              Field {currentFieldIndex + 1} of {allFields.length}
            </span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Current Field */}
        {currentField && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 space-y-6">
            <div>
              <p className="text-sm text-gray-500 mb-1">
                {currentField.sectionName}
              </p>
              <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                {currentField.label}
              </h2>
              {currentField.hint && (
                <p className="text-gray-600 italic">{currentField.hint}</p>
              )}
            </div>

            {/* Input Field */}
            <div>
              {currentField.type === 'paragraph' ? (
                <textarea
                  value={currentValue}
                  onChange={(e) => setCurrentValue(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  rows={5}
                  placeholder="Type your answer here..."
                />
              ) : currentField.type === 'enum' ? (
                <select
                  value={currentValue}
                  onChange={(e) => setCurrentValue(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select an option...</option>
                  {currentField.constraints.enum_values?.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : (
                <Input
                  type={
                    currentField.type === 'number'
                      ? 'number'
                      : currentField.type === 'date'
                        ? 'date'
                        : 'text'
                  }
                  value={currentValue}
                  onChange={(e) => setCurrentValue(e.target.value)}
                  placeholder="Type your answer here..."
                  className="text-lg"
                />
              )}
            </div>

            {/* Navigation */}
            <div className="flex gap-4">
              <Button
                onClick={goBack}
                variant="secondary"
                disabled={currentFieldIndex === 0}
                className="flex-1"
              >
                Back
              </Button>
              <Button
                onClick={saveField}
                disabled={isSaving}
                className="flex-1"
              >
                {isSaving
                  ? 'Saving...'
                  : currentFieldIndex < allFields.length - 1
                    ? 'Next'
                    : 'Complete'}
              </Button>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="mt-8 text-center">
          <button
            onClick={() => router.push('/dashboard')}
            className="text-gray-600 hover:text-gray-900 underline"
          >
            Save & Exit
          </button>
        </div>
      </div>
    </div>
  )
}
