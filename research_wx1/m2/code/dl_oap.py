import time
from huggingface_hub import hf_hub_download
t=time.time()
for i in range(6):
    try:
        p=hf_hub_download('OpenSourceAP/CrossSection', 'Firm Level Characteristics/Predictors.parquet', repo_type='dataset', revision='Data-Release-2026.10', local_dir='raw')
        print('done', p, time.time()-t, flush=True); break
    except Exception as e:
        print('retry', i, repr(e)[:200], flush=True); time.sleep(30*(i+1))
