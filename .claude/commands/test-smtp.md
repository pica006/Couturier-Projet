---
description: Teste la configuration SMTP (sans envoyer d'email) et affiche le diagnostic.
---

Exécute la commande suivante pour vérifier la configuration SMTP de l'app
(EMAIL_HOST, EMAIL_USER, EMAIL_PASSWORD, TLS/SSL, port) sans envoyer de message :

```bash
python -c "from controllers.email_controller import EmailController; ok, msg = EmailController().tester_connexion(); print('[OK]' if ok else '[KO]', msg)"
```

Si le test échoue :
1. Lis `.env` pour vérifier les variables `EMAIL_*`.
2. Pour Gmail, rappelle à l'utilisateur d'utiliser un mot de passe d'application
   (16 caractères, créé sur https://myaccount.google.com/apppasswords).
3. Vérifie le port : 465 = SSL implicite, 587 = STARTTLS.
4. Propose un `tester_connexion()` sur une config alternative si besoin.
