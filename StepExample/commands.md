# Commands

```bash
curl -X 'POST' \
  'http://localhost:8000/actions' \
  -H 'Content-Type: application/json' \
  -d '{
  "id": "run-motor-b",
  "pumpB": {
    "state": true,
    "speed": 4000,
    "dir": true
  },
  "time": 20000
}'
```

```bash
curl -X 'GET' 'http://localhost:8000/sensor' -H 'accept: application/json'
```

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
