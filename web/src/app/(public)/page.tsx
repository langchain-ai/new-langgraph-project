'use client'

import { signIn } from 'next-auth/react'
import { Button } from '@/components/shared/Button'

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center space-y-8 max-w-2xl px-4">
        <h1 className="text-6xl font-bold text-gray-900">VoicedForm</h1>
        <p className="text-xl text-gray-700">
          Complete forms using your voice. Fast, accurate, and effortless.
        </p>

        <div className="space-y-4">
          <Button
            onClick={() => signIn('google', { callbackUrl: '/dashboard' })}
            size="lg"
            className="bg-white text-gray-800 hover:bg-gray-50 border border-gray-300 shadow-lg"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Sign in with Google
          </Button>
        </div>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="space-y-2">
            <div className="text-4xl">🎙️</div>
            <h3 className="font-semibold text-lg">Voice Input</h3>
            <p className="text-sm text-gray-600">
              Speak naturally to fill out forms
            </p>
          </div>
          <div className="space-y-2">
            <div className="text-4xl">✅</div>
            <h3 className="font-semibold text-lg">Smart Validation</h3>
            <p className="text-sm text-gray-600">
              AI-powered field validation
            </p>
          </div>
          <div className="space-y-2">
            <div className="text-4xl">📄</div>
            <h3 className="font-semibold text-lg">PDF Export</h3>
            <p className="text-sm text-gray-600">
              Generate and email PDFs automatically
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
