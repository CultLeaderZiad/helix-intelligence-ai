import pathlib,json,time
source=pathlib.Path(__file__).with_name('capture-tabs.py').read_text().split('plans={')[0]
ns={'__file__':str(pathlib.Path(__file__))};exec(source,ns)
open_page=ns['open_page'];shot=ns['shot'];c=ns['c']
# Run only after other shared-browser captures finish; no external work is submitted.
