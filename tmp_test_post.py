import time, requests
for i in range(10):
    try:
        resp = requests.post('http://127.0.0.1:5000/check_heatwave', json={'lat':10,'lon':10}, timeout=5)
        print('status', resp.status_code)
        print(resp.json())
        break
    except Exception as e:
        print('attempt', i, 'failed', e)
        time.sleep(1)
