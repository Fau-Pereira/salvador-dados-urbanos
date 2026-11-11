import json
from datetime import datetime, timezone
from pathlib import Path
import requests
from sqlalchemy import text
from src.db import get_engine

# Diretório onde o JSON bruto será salvo
RAW_DIR = Path("data/raw")
RAW_FILE = RAW_DIR / "ibge_indicadores.json"

# Código IBGE de Salvador (7 dígitos)
MUNICIPIO_SALVADOR = "2927408"

# Catálogo de indicadores da API de Agregados do IBGE (v3)
INDICADORES_IBGE = [
    {
        "codigo_indicador": "IBGE_POP_CENSO",
        "nome_fonte": "IBGE - Censo Demográfico (População Residente - Agregado 4714)",
        "url": f"https://servicodados.ibge.gov.br/api/v3/agregados/4714/periodos/-6/variaveis/93?localidades=N6[{MUNICIPIO_SALVADOR}]",
    },
    {
        "codigo_indicador": "IBGE_POP_ESTIMADA",
        "nome_fonte": "IBGE - Estimativas de População (Agregado 6579)",
        "url": f"https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/-6/variaveis/9324?localidades=N6[{MUNICIPIO_SALVADOR}]",
    },
    {
        "codigo_indicador": "IBGE_PIB_MUNICIPAL",
        "nome_fonte": "IBGE - PIB dos Municípios a preços correntes (Agregado 5938)",
        "url": f"https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos/-6/variaveis/37?localidades=N6[{MUNICIPIO_SALVADOR}]",
    },
]


def registrar_fonte(nome: str, url: str) -> int:
    """Registra a coleta na tabela raw.fontes e retorna o id gerado."""
    engine = get_engine()
    query = text(
        """
        INSERT INTO raw.fontes (nome, url)
        VALUES (:nome, :url)
        RETURNING id;
        """
    )
    with engine.begin() as conn:
        fonte_id = conn.execute(query, {"nome": nome, "url": url}).scalar_one()
    return int(fonte_id)


def extrair_indicadores_ibge() -> Path:
    """Consulta a API do IBGE, registra a fonte no banco e salva o JSON bruto."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    coletas = []

    for item in INDICADORES_IBGE:
        codigo = item["codigo_indicador"]
        url = item["url"]
        print(f"[EXTRACT] Consultando {codigo} na API do IBGE...")

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        dados_api = response.json()

        fonte_id = registrar_fonte(nome=item["nome_fonte"], url=url)
        print(f"  -> Fonte registrada em raw.fontes com id={fonte_id}")

        coletas.append(
            {
                "codigo_indicador": codigo,
                "nome_fonte": item["nome_fonte"],
                "url": url,
                "fonte_id": fonte_id,
                "data_coleta": datetime.now(timezone.utc).isoformat(),
                "resposta_api": dados_api,
            }
        )

    with open(RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(coletas, f, ensure_ascii=False, indent=2)

    print(f"[EXTRACT] Arquivo bruto salvo com sucesso em: {RAW_FILE}")
    return RAW_FILE


if __name__ == "__main__":
    extrair_indicadores_ibge()
