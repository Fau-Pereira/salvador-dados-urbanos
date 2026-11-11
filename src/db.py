import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL

# Carrega as variáveis do arquivo .env
load_dotenv()


def get_db_url() -> URL:
    """Monta a URL de conexão de forma segura (tratando caracteres especiais como '@' na senha)."""
    return URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "urban_dev"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "salvador_urban"),
    )


def get_engine() -> Engine:
    """Retorna a instância do Engine do SQLAlchemy para conexão com o PostGIS."""
    return create_engine(get_db_url(), pool_pre_ping=True)


def test_connection() -> None:
    """Testa a conexão com o banco e exibe a versão do PostgreSQL e do PostGIS."""
    engine = get_engine()
    with engine.connect() as conn:
        pg_version = conn.execute(text("SELECT version();")).scalar()
        postgis_version = conn.execute(text("SELECT PostGIS_Version();")).scalar()
        print("Conexão realizada com sucesso!")
        print(f"PostgreSQL: {pg_version}")
        print(f"PostGIS:    {postgis_version}")


if __name__ == "__main__":
    test_connection()
