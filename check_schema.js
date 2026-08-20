import { neon } from '@neondatabase/serverless';

async function check() {
  try {
    const sql = neon(process.env.DATABASE_URL);
    
    console.log('--- SCHEMAS ---');
    const schemas = await sql`SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_toast', 'pg_catalog', 'information_schema');`;
    console.log(schemas);

    console.log('\n--- TABLES ---');
    const tables = await sql`SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema');`;
    console.log(tables);

    console.log('\n--- ROLES ---');
    const roles = await sql`SELECT rolname FROM pg_roles WHERE rolname NOT LIKE 'pg_%';`;
    console.log(roles);
    
  } catch (err) {
    console.error('Failed:', err);
    process.exit(1);
  }
}

check();
