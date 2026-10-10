import re
def system_of(name):
    n=name.lower()
    if 'carotid sinus' in n: return 'arterial'
    if re.search(r'skin of',n): return 'skin'
    if re.search(r'nerve|ganglion|ansa |ansa$|cauda equina|neural tissue|olfactory tract|chiasm|gyrus|nucleus|tract of|substantia nigra|cuneus|stria terminalis|plexus of lateral ventricle|choroid plexus',n): return 'nervous'
    if re.search(r'venous plexus|pterygoid plexus|vein|sinus|venous|diploic|emissary',n): return 'venous'
    if re.search(r'arter|aorta|arch|branch of .*(artery|carotid)|trunk of .*artery',n): return 'arterial'
    if re.search(r'bronch|parenchyma',n): return 'respiratory'
    if re.search(r'thyroid gland|parathyroid',n): return 'endocrine'
    if re.search(r'costal cartilage|bone|plate of ethmoid|alar cartilage|septal nasal cartilage',n): return 'skeletal'
    if re.search(r'cornea|sclera|choroid$|lens',n): return 'sensory'
    if re.search(r'ligament|falx|dura mater|tentorium|conus elasticus',n): return 'connective'
    if re.search(r'sternocleidomastoid|aryepiglotticus|cricothyroid|muscle',n): return 'muscular'
    if re.search(r'gingiva|peritoneum',n): return 'digestive'
    return None
