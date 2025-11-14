import { requireAuth, getCurrentUserId } from '@/lib/auth'
import { supabaseAdmin } from '@/lib/supabase'
import { TemplateCard } from '@/components/dashboard/TemplateCard'
import { RecentSessions } from '@/components/dashboard/RecentSessions'
import Link from 'next/link'
import { Button } from '@/components/shared/Button'

export default async function DashboardPage() {
  await requireAuth()
  const userId = await getCurrentUserId()

  // Fetch templates
  const { data: templates } = await supabaseAdmin
    .from('templates')
    .select('*')
    .eq('owner_user_id', userId)
    .is('deleted_at', null)
    .order('updated_at', { ascending: false })

  // Fetch recent sessions
  const { data: recentSessions } = await supabaseAdmin
    .from('form_sessions')
    .select('*, template:templates(name)')
    .eq('user_id', userId)
    .order('updated_at', { ascending: false })
    .limit(5)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">
            VoicedForm Dashboard
          </h1>
          <div className="flex gap-4">
            <Link href="/templates/new">
              <Button>Create Template</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 space-y-8">
        {/* Templates Section */}
        <section>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              My Templates
            </h2>
          </div>

          {templates && templates.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {templates.map((template) => (
                <TemplateCard key={template.id} template={template} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
              <div className="text-6xl mb-4">📝</div>
              <p className="text-gray-600 mb-4 text-lg">
                No templates yet. Create your first template to get started!
              </p>
              <Link href="/templates/new">
                <Button>Create Template</Button>
              </Link>
            </div>
          )}
        </section>

        {/* Recent Sessions */}
        {recentSessions && recentSessions.length > 0 && (
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Recent Sessions
            </h2>
            <RecentSessions sessions={recentSessions} />
          </section>
        )}
      </main>
    </div>
  )
}
