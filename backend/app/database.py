import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Se rodar na Vercel ou local com postgresql, usa a URL fornecida.
# Caso contrário, usa o SQLite local.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./argos_armazem.db")

# Ajuste para garantir compatibilidade com versões antigas de URLs do Heroku/PostgreSQL (caso use 'postgres://')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite exige o argumento connect_args={"check_same_thread": False}
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependência para obter a sessão do banco de dados nas rotas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
