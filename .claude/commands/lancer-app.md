---
description: Lance l'app Streamlit en local avec vérification préalable.
---

1. Vérifie que `.env` est bien rempli (`cat .env | head -20`).
2. Compile le code pour éviter les SyntaxError au boot :
   ```bash
   python -m compileall -q .
   ```
3. Lance l'application :
   ```bash
   streamlit run app.py
   ```

Si un `ImportError` survient :
- `pip install -r requirements.txt`
- Vérifier la version Python : `python --version` (3.11+ requis).
