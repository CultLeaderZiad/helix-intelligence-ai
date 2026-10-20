import pathlib,json,time
source=pathlib.Path(__file__).with_name('capture-tabs.py').read_text().split('plans={')[0]
ns={'__file__':str(pathlib.Path(__file__))};exec(source,ns)
open_page=ns['open_page'];shot=ns['shot'];click_label=ns['click_label'];c=ns['c']
for lang in ['en','ar']:
 open_page('/create',lang)
 for category,labels in [('Image Creative',['Quick Concept','Commercial Ad Still','Storyboard Frame','Graphic Layout']),('Video Motion',['Ad Concept (Short)','Explainer','UGC Clip'])]:
  click_label(category)
  # Select only mode cards, not generation/dispatch actions.
  for label in labels:
   result=c.ev('''(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes(LABEL)&&x.className.includes('border'));if(!b)return {clicked:false};b.click();return {clicked:true,label:b.textContent.trim()}})()'''.replace('LABEL',json.dumps(label)))
   shot('/create',lang,category+'-'+label,result)
 open_page('/discover',lang)
 result=c.ev('''(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('Filters')||x.textContent.includes('تصفية النتائج'));if(!b)return {clicked:false};b.click();return {clicked:true}})()''')
 shot('/discover',lang,'filters',result)
 result=c.ev('''(()=>{const b=[...document.querySelectorAll('button')].find(x=>x.textContent.includes('Drafts & History')||x.textContent.includes('المسودات'));if(!b)return {clicked:false};b.click();return {clicked:true}})()''')
 shot('/discover',lang,'drafts-history',result)
