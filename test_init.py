import ee, traceback, os
print('EE_PROJECT=', os.environ.get('EE_PROJECT'))
try:
    ee.Initialize(project='propane-library-477610-c3')
    print('Initialize OK')
except Exception:
    traceback.print_exc()
