import importlib.util
spec = importlib.util.spec_from_file_location('m', r'C:\Users\Richard\Documents\RAG\math_cli_v10.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.explain_salt()
