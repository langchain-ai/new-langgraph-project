import { getServerSession, NextAuthOptions } from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'
import { supabaseAdmin } from './supabase'

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async signIn({ user, account }) {
      if (!user.email || !account) return false

      try {
        // Create or update user in Supabase
        const { error } = await supabaseAdmin.from('users').upsert(
          {
            auth_provider_id: account.providerAccountId,
            email: user.email,
            name: user.name || null,
            avatar_url: user.image || null,
            last_login_at: new Date().toISOString(),
          },
          { onConflict: 'auth_provider_id' }
        )

        if (error) {
          console.error('Error upserting user:', error)
          return false
        }

        return true
      } catch (error) {
        console.error('Sign in error:', error)
        return false
      }
    },
    async jwt({ token, account }) {
      if (account) {
        token.providerAccountId = account.providerAccountId
      }
      return token
    },
    async session({ session, token }) {
      try {
        // Fetch user ID from Supabase
        const { data } = await supabaseAdmin
          .from('users')
          .select('id')
          .eq('auth_provider_id', token.providerAccountId as string)
          .single()

        if (data) {
          session.user.id = data.id
        }

        return session
      } catch (error) {
        console.error('Session callback error:', error)
        return session
      }
    },
  },
  pages: {
    signIn: '/',
  },
  secret: process.env.NEXTAUTH_SECRET,
}

export async function requireAuth() {
  const session = await getServerSession(authOptions)
  if (!session) {
    throw new Error('Unauthorized')
  }
  return session
}

export async function getCurrentUserId(): Promise<string> {
  const session = await requireAuth()
  if (!session.user?.id) {
    throw new Error('User ID not found in session')
  }
  return session.user.id
}
