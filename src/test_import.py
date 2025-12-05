import traceback

print("Python is running")
try:
    import api_app
    print("Imported api_app OK")
except Exception:
    print("Error while importing api_app:")
    traceback.print_exc()
