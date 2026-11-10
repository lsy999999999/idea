"""Resolve unambiguous structural locators without asking authors to reformat them."""
import re

def escape(value):return str(value).replace('~','~0').replace('/','~1')

def select(obj, locator):
    if locator in ('','/','$'):return obj,''
    if not isinstance(locator,str):raise ValueError('A field name or structural path is required')
    if locator.startswith('/'):
        tokens=[t.replace('~1','/').replace('~0','~') for t in locator[1:].split('/')]
    else:
        tokens=locator.removeprefix('$.').split('.') if '.' in locator else [locator]
    found=[]
    def walk(value,pos,path):
        if pos==len(tokens):found.append((value,path));return
        if isinstance(value,dict):
            for end in range(pos+1,len(tokens)+1):
                key='/'.join(tokens[pos:end])
                if key in value:walk(value[key],end,path+'/'+escape(key))
        elif isinstance(value,list) and tokens[pos].isdigit() and int(tokens[pos])<len(value):
            walk(value[int(tokens[pos])],pos+1,path+'/'+tokens[pos])
    walk(obj,0,'')
    if not found and not locator.startswith('/'):
        def names(value,path):
            if isinstance(value,dict):
                for key,item in value.items():
                    target=path+'/'+escape(key)
                    if key==locator:found.append((item,target))
                    names(item,target)
            elif isinstance(value,list):
                for i,item in enumerate(value):names(item,path+'/'+str(i))
        names(obj,'')
    distinct={path:(value,path) for value,path in found}
    if len(distinct)!=1:
        raise ValueError(('Ambiguous' if distinct else 'Unresolved')+' field locator '+repr(locator)+'; matching paths: '+repr(list(distinct)))
    return next(iter(distinct.values()))
