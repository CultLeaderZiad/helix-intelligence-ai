import pathlib,sys,json,time
from importlib.machinery import SourceFileLoader
c=SourceFileLoader('capturetabs',str(pathlib.Path(__file__).with_name('capture-tabs.py')))
# Import the reusable helpers without executing the capture plan again.
source=pathlib.Path(__file__).with_name('capture-tabs.py').read_text().split('plans={')[0]
ns={'__file__':str(pathlib.Path(__file__))};exec(source,ns)
open_page=ns['open_page'];shot=ns['shot'];click_label=ns['click_label'];core=ns['c']
labels=['Helix-Architecture-The-4-Loops','Discover-Competitor-Ad-Extraction','Intelligence-Pattern-Synthesis-Teardowns','Create-Studio-AI-Generation','Performance-Longevity-Fatigue-Tracking','Admin-Center-Operations']
for lang in ['en','ar']:
 for path in ['/guide','/admin/guide']:
  open_page(path,lang)
  for index,label in enumerate(labels):
   result=core.ev('''(()=>{const b=[...document.querySelectorAll('button')].filter(x=>x.className.includes('items-start')&&x.className.includes('p-3'))[INDEX];if(!b)return {clicked:false};b.click();return {clicked:true,label:b.textContent.trim()}})()'''.replace('INDEX',str(index)))
   shot(path,lang,label,result)
 open_page('/admin/updates',lang);click_label('New Update');result=click_label('Kie.ai Card Preview');shot('/admin/updates',lang,'preview',result)
 open_page('/admin/support',lang)
 fields=core.ev('[...document.querySelectorAll("select")].map((s,i)=>({index:i,options:[...s.options].map(o=>({value:o.value,label:o.textContent}))}))')
 for field in fields:
  for option in field['options']:
   result=core.ev('''(()=>{const s=document.querySelectorAll('select')[INDEX];s.value=VALUE;s.dispatchEvent(new Event('change',{bubbles:true}));return {selected:s.value}})()'''.replace('INDEX',str(field['index'])).replace('VALUE',json.dumps(option['value'])))
   shot('/admin/support',lang,option['label'],result)
