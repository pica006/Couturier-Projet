---
description: Compile tout le code et vérifie les imports critiques.
---

Exécute ces vérifications :

```bash
python -m compileall -q .
python -c "from controllers.email_controller import EmailController; print('OK email')"
python -c "from controllers.pdf_controller import PDFController; print('OK pdf')"
python -c "from controllers.rappel_service import executer_rappels_automatiques; print('OK rappels')"
python -c "from utils.theme import get_login_css, get_sidebar_bg_css; print('OK theme')"
python -c "from config import EMAIL_CONFIG, APP_CONFIG; print('OK config')"
```

Rapporte au format :
- [OK] ou [KO] <module> : <erreur si KO>

Si un module échoue, grep le fichier concerné pour trouver la ligne fautive.
