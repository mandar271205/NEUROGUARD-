import { createClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const { userId } = await request.json();

    if (!userId) {
      return NextResponse.json({ error: 'User ID is required' }, { status: 400 });
    }

    const supabaseAdmin = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
      {
        auth: {
          autoRefreshToken: false,
          persistSession: false
        }
      }
    );

    const { error } = await supabaseAdmin.auth.admin.updateUserById(
      userId,
      { email_confirm: true }
    );

    if (error) {
      console.error('Error auto-confirming user:', error);
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    return NextResponse.json({ message: 'User confirmed successfully' });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Auto-confirm failed';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
