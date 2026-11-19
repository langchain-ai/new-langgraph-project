'use client'

import { FormSessionWithTemplate } from '@/types/database'
import Link from 'next/link'

interface RecentSessionsProps {
  sessions: (FormSessionWithTemplate & { template: { name: string } | null })[]
}

export function RecentSessions({ sessions }: RecentSessionsProps) {
  const getStatusBadge = (status: string) => {
    const badges = {
      draft: 'bg-gray-100 text-gray-800',
      in_progress: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      sent: 'bg-purple-100 text-purple-800',
    }

    return (
      <span
        className={`px-2 py-1 text-xs font-medium rounded-full ${badges[status as keyof typeof badges] || 'bg-gray-100 text-gray-800'}`}
      >
        {status.replace('_', ' ')}
      </span>
    )
  }

  const getLink = (session: typeof sessions[0]) => {
    if (session.status === 'completed' || session.status === 'sent') {
      return `/forms/${session.id}/review`
    }
    return `/forms/${session.id}`
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="divide-y divide-gray-200">
        {sessions.map((session) => (
          <Link
            key={session.id}
            href={getLink(session)}
            className="block hover:bg-gray-50 transition-colors"
          >
            <div className="px-6 py-4">
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-medium text-gray-900">
                    {session.template?.name || 'Unknown Template'}
                  </h4>
                  <p className="text-sm text-gray-600 mt-1">
                    Started {new Date(session.created_at).toLocaleString()}
                  </p>
                  {session.completed_at && (
                    <p className="text-sm text-gray-600">
                      Completed{' '}
                      {new Date(session.completed_at).toLocaleString()}
                    </p>
                  )}
                </div>
                <div>{getStatusBadge(session.status)}</div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
