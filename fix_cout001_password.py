"""
Script unique : vérifie/met à jour le mot de passe de COUT001 vers admin123 (bcrypt).
À exécuter depuis la racine du projet : python fix_cout001_password.py
"""
import os
import sys

# Charger .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def main():
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    database = os.getenv("DB_NAME", "db_couturier")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")

    if not password:
        print("ERREUR: DB_PASSWORD manquant dans .env")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("ERREUR: psycopg2 non installé. Lancez: pip install psycopg2-binary")
        sys.exit(1)

    from utils.security import hash_password, verify_password

    code = "COUT001"
    plain_password = "admin123"
    password_hash = hash_password(plain_password)

    print(f"Connexion à PostgreSQL ({host}:{port}/{database})...")
    try:
        conn = psycopg2.connect(
            host=host, port=port, database=database, user=user, password=password,
            connect_timeout=10
        )
    except Exception as e:
        print(f"ERREUR connexion: {e}")
        sys.exit(1)

    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, code_couturier, password FROM couturiers WHERE code_couturier = %s",
            (code,)
        )
        row = cur.fetchone()
        if not row:
            print(f"Utilisateur {code} introuvable. Création...")
            cur.execute(
                """
                INSERT INTO couturiers (code_couturier, password, nom, prenom, role, actif)
                VALUES (%s, %s, 'Admin', 'Test', 'admin', TRUE)
                """,
                (code, password_hash)
            )
            conn.commit()
            print(f"OK: Utilisateur {code} créé avec mot de passe 'admin123' (bcrypt).")
        else:
            stored = row[2]
            if verify_password(plain_password, stored):
                print(f"OK: {code} existe déjà et le mot de passe 'admin123' est valide.")
            else:
                cur.execute(
                    "UPDATE couturiers SET password = %s WHERE code_couturier = %s",
                    (password_hash, code)
                )
                conn.commit()
                print(f"OK: Mot de passe de {code} mis à jour vers 'admin123' (bcrypt).")
    finally:
        cur.close()
        conn.close()
    print("Vous pouvez vous connecter avec: Code COUT001, Mot de passe admin123")

if __name__ == "__main__":
    main()
