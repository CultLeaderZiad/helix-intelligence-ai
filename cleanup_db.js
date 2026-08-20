import { neon } from '@neondatabase/serverless';

async function cleanup() {
  try {
    const sql = neon(process.env.DATABASE_URL);
    
    console.log('Dropping schema neon_auth...');
    await sql`DROP SCHEMA IF EXISTS neon_auth CASCADE;`;
    
    console.log('Dropping role neon_auth...');
    try {
      await sql`DROP ROLE IF EXISTS neon_auth;`;
    } catch (e) {
      console.log('Could not drop role neon_auth (might have permissions issues or dependents):', e.message);
    }
    
    console.log('\n--- VERIFYING CURRENT SCHEMAS ---');
    const schemas = await sql`SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_toast', 'pg_catalog', 'information_schema');`;
    console.log(schemas);

    console.log('\n--- VERIFYING public TABLES ---');
    const tables = await sql`SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema = 'public';`;
    console.log(tables);

    console.log('\n--- VERIFYING COUNTS IN public.users & public.organizations ---');
    const userCount = await sql`SELECT COUNT(*) FROM public.users;`;
    console.log('Users count:', userCount[0].count);
    const orgCount = await sql`SELECT COUNT(*) FROM public.organizations;`;
    console.log('Organizations count:', orgCount[0].count);
    
  } catch (err) {
    console.error('Failed:', err);
    process.exit(1);
  }
}

cleanup();
