'use client'

import { Template } from '@/types/database'
import Link from 'next/link'
import { Button } from '@/components/shared/Button'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

interface TemplateCardProps {
  template: Template
}

export function TemplateCard({ template }: TemplateCardProps) {
  const router = useRouter()
  const [isDeleting, setIsDeleting] = useState(false)

  const fieldCount = template.schema.sections.reduce(
    (sum, section) => sum + section.fields.length,
    0
  )

  const startForm = async () => {
    try {
      const response = await fetch('/api/forms/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_id: template.id }),
      })

      if (!response.ok) throw new Error('Failed to create form session')

      const data = await response.json()
      router.push(`/forms/${data.session_id}`)
    } catch (error) {
      console.error('Error starting form:', error)
      alert('Failed to start form. Please try again.')
    }
  }

  const deleteTemplate = async () => {
    if (
      !confirm(
        `Are you sure you want to delete "${template.name}"? This cannot be undone.`
      )
    ) {
      return
    }

    setIsDeleting(true)
    try {
      const response = await fetch(`/api/templates/${template.id}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error.message)
      }

      router.refresh()
    } catch (error) {
      console.error('Error deleting template:', error)
      alert((error as Error).message)
      setIsDeleting(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {template.name}
          </h3>
          {template.description && (
            <p className="text-sm text-gray-600 mt-1">{template.description}</p>
          )}
        </div>
      </div>

      <div className="text-sm text-gray-500 space-y-1 mb-4">
        <p>{template.schema.sections.length} sections</p>
        <p>{fieldCount} fields</p>
        <p className="text-xs">
          Updated {new Date(template.updated_at).toLocaleDateString()}
        </p>
      </div>

      <div className="flex gap-2">
        <Button onClick={startForm} size="sm" className="flex-1">
          Start Form
        </Button>
        <Link href={`/templates/${template.id}`}>
          <Button variant="secondary" size="sm">
            Edit
          </Button>
        </Link>
        <Button
          variant="danger"
          size="sm"
          onClick={deleteTemplate}
          disabled={isDeleting}
        >
          {isDeleting ? '...' : 'Delete'}
        </Button>
      </div>
    </div>
  )
}
