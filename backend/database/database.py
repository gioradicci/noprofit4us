import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Costruiamo il percorso assoluto al file .env (che si trova una cartella più in alto rispetto a database.py)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path, override=True)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    # ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
    # ALTER TABLE public.members ENABLE ROW LEVEL SECURITY;
    # ALTER TABLE public.memberships ENABLE ROW LEVEL SECURITY;
    # ALTER TABLE public.gadgets ENABLE ROW LEVEL SECURITY;
    # ALTER TABLE public.gadget_variants ENABLE ROW LEVEL SECURITY;
    # ALTER TABLE public.warehouses ENABLE ROW LEVEL SECURITY;
    # ALTER TABLE public.gadget_variant_stocks ENABLE ROW LEVEL SECURITY;
    # ALTER TABLE public.stock_movements ENABLE ROW LEVEL SECURITY;
    # ALTER TABLE public.gadget_locks ENABLE ROW LEVEL SECURITY;
    # ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def initialize_database():
    from database.base import Base
    
    # Importiamo tutti i modelli per registrarli nel metadata di Base
    try:
        from database.models.user import User
        from database.models.member import Member
        from database.models.membership import Membership
        from database.models.gadget import Gadget, GadgetVariant, Warehouse, GadgetVariantStock, StockMovement, GadgetLock
        from database.models.audit import AuditLog
    except ImportError as e:
        print("WARNING: Errore durante l'importazione dei modelli:", e)

    # 1. Creazione delle tabelle
    print("Inizializzazione delle tabelle del database...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Configurazione automatica dei permessi e del trigger se siamo su PostgreSQL
    if not DATABASE_URL.startswith("sqlite"):
        from sqlalchemy import text
        print("Rilevato PostgreSQL (Supabase). Configurazione automatica dei permessi e del trigger di sincronizzazione...")
        
        trigger_sql_function = """
        CREATE OR REPLACE FUNCTION public.handle_new_user() 
        RETURNS trigger AS $$
        DECLARE
          is_first_user BOOLEAN;
          default_role VARCHAR;
          default_roles_json JSONB;
        BEGIN
          -- Controlla se questo è il primissimo utente inserito nel database
          SELECT NOT EXISTS (SELECT 1 FROM public.users LIMIT 1) INTO is_first_user;
          
          IF is_first_user THEN
            default_role := 'ADMIN';
            default_roles_json := '["ADMIN"]'::jsonb;
          ELSE
            default_role := 'USER';
            default_roles_json := '["USER"]'::jsonb;
          END IF;

          -- Impostiamo il ruolo in raw_app_meta_data di auth.users
          UPDATE auth.users
          SET raw_app_meta_data = jsonb_set(
            COALESCE(raw_app_meta_data, '{}'::jsonb), 
            '{roles}', 
            default_roles_json
          )
          WHERE id = NEW.id;

          -- Inseriamo automaticamente la riga in public.users
          INSERT INTO public.users (auth0_id, email, role, status)
          VALUES (
            NEW.id::text, 
            NEW.email, 
            default_role, 
            'INCOMPLETE'
          )
          ON CONFLICT (auth0_id) DO NOTHING;
          
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
        
        trigger_sql_association = """
        DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
        CREATE TRIGGER on_auth_user_created
          AFTER INSERT ON auth.users
          FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
        """
        
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                # Concediamo permessi sullo schema public
                conn.execute(text("GRANT ALL ON SCHEMA public TO postgres;"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO PUBLIC;"))
                
                # Abilitiamo RLS su tutte le tabelle per sicurezza
                tables_to_secure = [
                    "users", "members", "memberships", "gadgets", 
                    "gadget_variants", "warehouses", "gadget_variant_stocks", 
                    "stock_movements", "gadget_locks", "audit_logs"
                ]
                for table in tables_to_secure:
                    conn.execute(text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;"))
                
                # Creiamo la funzione
                conn.execute(text(trigger_sql_function))
                
                # Creiamo il trigger
                conn.execute(text(trigger_sql_association))
                
                trans.commit()
                print("Trigger di sincronizzazione e permessi configurati con successo su PostgreSQL!")
            except Exception as e:
                trans.rollback()
                print("WARNING: Impossibile applicare trigger o permessi sul DB:", str(e))
