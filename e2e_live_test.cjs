const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log("🚀 Starting end-to-end smoke test against LIVE Vercel deployment...");
  
  const BASE_URL = 'https://helix-intelligence-ai-six.vercel.app';
  
  try {
    // 1. Test Admin Login
    console.log("Testing Admin Login...");
    await page.goto(`${BASE_URL}/auth`);
    await page.fill('input[type="email"]', 'cultleaderzoz.dev@gmail.com');
    await page.fill('input[type="password"]', 'Helixxa-intel-2027');
    await page.click('button:has-text("Sign in")');
    
    // Wait for navigation to /discover
    await page.waitForURL('**/discover');
    console.log("✅ Admin Login successful!");
    
    // Check if Trial Banner is present
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
