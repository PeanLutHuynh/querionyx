# Backend Entrypoint Note

Run from repository root:

```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

For Render with `rootDir: backend`, use:

```powershell
uvicorn main:app --host 0.0.0.0 --port $PORT
```

