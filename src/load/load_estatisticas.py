from pathlib import Path
import pandas as pd
from sqlalchemy import text
from src.db import get_engine

PROCESSED_FILE = Path("data/processed/indicadores_tratados.csv")


def carregar_estatisticas() -> None:
    """Carrega os municípios, indicadores e observações tratadas no schema core."""
    if not PROCESSED_FILE.exists():
        raise FileNotFoundError(
            f"Arquivo processado não encontrado em {PROCESSED_FILE}. Execute o passo 1.2 antes."
        )

    df = pd.read_csv(PROCESSED_FILE, dtype={"codigo_ibge": str})
    engine = get_engine()

    with engine.begin() as conn:
        # 1. Garantir municípios em core.municipios
        municipios = df[["codigo_ibge", "municipio_nome", "uf"]].drop_duplicates()
        sql_municipio = text(
            """
            INSERT INTO core.municipios (codigo_ibge, nome, uf)
            VALUES (:codigo_ibge, :nome, :uf)
            ON CONFLICT (codigo_ibge) DO UPDATE
            SET nome = EXCLUDED.nome,
                uf = EXCLUDED.uf;
            """
        )
        for _, row in municipios.iterrows():
            conn.execute(
                sql_municipio,
                {
                    "codigo_ibge": row["codigo_ibge"].zfill(7),
                    "nome": row["municipio_nome"],
                    "uf": row["uf"],
                },
            )

        # 2. Garantir catálogo em core.indicadores e mapear os IDs
        indicadores = df[
            ["codigo_indicador", "nome_indicador", "unidade"]
        ].drop_duplicates()
        sql_indicador = text(
            """
            INSERT INTO core.indicadores (codigo_indicador, nome, unidade)
            VALUES (:codigo_indicador, :nome, :unidade)
            ON CONFLICT (codigo_indicador) DO UPDATE
            SET nome = EXCLUDED.nome,
                unidade = EXCLUDED.unidade
            RETURNING id;
            """
        )
        mapa_indicadores: dict[str, int] = {}
        for _, row in indicadores.iterrows():
            ind_id = conn.execute(
                sql_indicador,
                {
                    "codigo_indicador": row["codigo_indicador"],
                    "nome": row["nome_indicador"],
                    "unidade": row["unidade"],
                },
            ).scalar_one()
            mapa_indicadores[row["codigo_indicador"]] = int(ind_id)

        # 3. Inserir/atualizar séries históricas em core.observacoes
        sql_observacao = text(
            """
            INSERT INTO core.observacoes (
                codigo_ibge, indicador_id, ano_referencia, valor, fonte_id
            )
            VALUES (
                :codigo_ibge, :indicador_id, :ano_referencia, :valor, :fonte_id
            )
            ON CONFLICT (codigo_ibge, indicador_id, ano_referencia) DO UPDATE
            SET valor = EXCLUDED.valor,
                fonte_id = EXCLUDED.fonte_id;
            """
        )

        total_obs = 0
        for _, row in df.iterrows():
            conn.execute(
                sql_observacao,
                {
                    "codigo_ibge": row["codigo_ibge"].zfill(7),
                    "indicador_id": mapa_indicadores[row["codigo_indicador"]],
                    "ano_referencia": int(row["ano_referencia"]),
                    "valor": float(row["valor"]),
                    "fonte_id": int(row["fonte_id"]),
                },
            )
            total_obs += 1

    print(
        f"[LOAD] Carga concluída! {len(municipios)} município(s), "
        f"{len(mapa_indicadores)} indicador(es) e {total_obs} observações gravadas no PostgreSQL."
    )


if __name__ == "__main__":
    carregar_estatisticas()
