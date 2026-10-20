import pathlib,json,time,os
source=pathlib.Path(__file__).with_name('capture-tabs.py').read_text().split('plans={')[0]
ns={'__file__':str(pathlib.Path(__file__))};exec(source,ns)
open_page=ns['open_page'];shot=ns['shot'];c=ns['c']
# Run only after other shared-browser captures finish; no external work is submitted.
c.browser('press','Escape');c.ev('localStorage.setItem("helix_lang","en");true');c.browser('open',c.BASE+'/discover');c.browser('wait','--load','networkidle')
c.ev('document.querySelector("button[aria-label=\\\"Sign out\\\"]")?.click();true')
c.browser('open',c.BASE+'/sign-in');c.browser('wait','input[type=email]');c.browser('fill','input[type=email]','audit-member@example.com');c.browser('fill','input[type=password]',os.environ['AUDIT_BROWSER_PASSWORD']);c.browser('click','button[type=submit]')
c.browser('wait','--load','networkidle')
for lang in ['en','ar']:
 for path in ['/discover','/create','/billing']:
  open_page(path,lang);shot(path,lang,'pending-access',{'identity':'local pending member; no provider dispatch'})
# Leave the preview signed out; no credentials/tokens are published in evidence.
c.ev('document.querySelector("button[aria-label=\\\"Sign out\\\"]")?.click();true')
c.browser('open',c.BASE+'/')
