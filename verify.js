import { neon } from '@neondatabase/serverless';

async function verify() {
  try {
    const sql = neon(process.env.DATABASE_URL);
    const result = await sql`SELECT 1 as result`;
    console.log('Connection successful:', result);
  } catch (err) {
    console.error('Connection failed:', err);
    process.exit(1);
  }
}

verify();
