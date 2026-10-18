const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const FRONTEND_URL = process.env.E2E_FRONTEND_URL || process.env.FRONTEND_URL || "";
  const adminEmail = process.env.E2E_ADMIN_EMAIL || process.env.ADMIN_EMAIL || "";
  const adminPassword = process.env.E2E_ADMIN_PASSWORD || process.env.ADMIN_PASSWORD || "";
  if (!FRONTEND_URL || !adminEmail || !adminPassword) {
    console.error("Refusing to start: set E2E_FRONTEND_URL, E2E_ADMIN_EMAIL, and E2E_ADMIN_PASSWORD from an isolated test environment.");
    process.exit(1);
  }
  const productionHosts = ["helix-intelligence-ai-six.vercel.app", "helix-intelligence-ai.onrender.com"];
  if (productionHosts.some((host) => FRONTEND_URL.includes(host))) {
    console.error("Refusing to start: this smoke test must not target the production frontend.");
    process.exit(1);
  }
  console.log("Starting end-to-end smoke test against an isolated frontend...");
  
  try {
    // Add console listener
    page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
    page.on('pageerror', err => console.log('BROWSER ERROR:', err.message));
    page.on('requestfailed', request => console.log('REQUEST FAILED:', request.url(), request.failure().errorText));

    // 1. Test Admin Login
    console.log("Testing Admin Login...");
    await page.goto(`${FRONTEND_URL}/auth`);
    await page.waitForLoadState('networkidle');
    await page.fill('input[type="email"]', adminEmail);
    await page.fill('input[type="password"]', adminPassword);
    
    // Take screenshot before clicking
    await page.screenshot({ path: 'login_before_click.png' });
    
    await Promise.all([
      page.waitForResponse(resp => resp.url().includes('/auth') && resp.status() !== 204).then(r => console.log('Auth API Response:', r.status(), r.url())),
      page.click('button:has-text("Sign in")')
    ]);
    
    // Wait a bit for navigation or error to show
    await page.waitForTimeout(5000);
    await page.screenshot({ path: 'login_after_click.png' });
    
    try {
      await page.waitForURL('**/discover', { timeout: 10000 });
      console.log("✅ Admin Login successful!");
    } catch (e) {
      console.log("❌ Failed to navigate to /discover within 10s. See login_after_click.png for UI state.");
    }
    console.log("Checking Trial Banner...");
    const banner = page.locator('text=You are currently on a 7-day free trial');
    const bannerCount = await banner.count();
    if (bannerCount > 0) {
      console.log("✅ Trial Banner is visible.");
    } else {
      console.log("⚠️ Trial Banner NOT visible. (Maybe this user is not on a trial or the copy changed)");
    }
    
    // Test Sign Out
    console.log("Testing Sign Out...");
    // Open sidebar or profile menu to sign out
    await page.click('button:has-text("Admin")');
    await page.click('text=Log out');
    await page.waitForURL('**/auth');
    console.log("✅ Sign Out successful!");

    // 2. Test Real Signup
    console.log("Testing Real Signup...");
    const testEmail = `test_live_${Date.now()}@vynex.com`;
    await page.click('text=Sign up');
    await page.fill('input[placeholder="name@company.com"]', testEmail);
    await page.fill('input[type="password"]', 'LiveTest123!');
    await page.click('button:has-text("Create account")');
    
    await page.waitForURL('**/discover');
    console.log(`✅ Signup successful with email: ${testEmail}`);
    
    // Check Trial Banner for new user
    await page.waitForSelector('text=7-day free trial', { timeout: 5000 }).catch(() => null);
    const newBannerCount = await page.locator('text=7-day free trial').count();
    if (newBannerCount > 0) {
      console.log("✅ Trial Banner is visible for the new user.");
    } else {
      console.log("❌ Trial Banner missing for new user.");
    }
    
    // 3. Test Discover Search (Confirm no zombie job hang)
    console.log("Testing Discover Search...");
    // Find the search input
    await page.fill('input[placeholder="Search competitors..."]', 'Nike running shoes');
    await page.click('button:has-text("Run discovery")');
    
    // Wait for job to progress or finish
    // Check if it's stuck on 'queued' or progresses
    console.log("Waiting for discovery job to run...");
    let isStuck = false;
    try {
      await page.waitForSelector('text=Job completed', { timeout: 30000 });
      console.log("✅ Discovery job finished (No zombie hang!).");
    } catch (e) {
      // Check if it's at least scraping something and not stuck on queued
      const scrapingText = await page.locator('text=Scraping').count();
      if (scrapingText > 0) {
         console.log("✅ Discovery job is running and progressing (No zombie hang!).");
      } else {
         console.log("❌ Discovery job might be hung or timed out.");
         isStuck = true;
      }
    }
    
  } catch (error) {
    console.error("❌ Test failed:", error);
  } finally {
    await browser.close();
  }
})();
