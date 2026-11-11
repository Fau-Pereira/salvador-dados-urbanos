import json
from pathlib import Path
import pandas as pd

RAW_FILE = Path("data/raw/ibge_indicadores.json")
PROCESSED_DIR = Path("data/processed")
PROCESSED_FILE = PROCESSED_DIR / "indicadores_tratados.csv"

# Símbolos que o IBGE utiliza para valores ausentes/sigilosos/não aplicáveis
VALORES_NULOS_IBGE = {"-", "..", "...", "X", "", None}


def separar_municipio_uf(nome_completo: str) -> tuple[str, str]:
    """Separa 'Salvador - BA' em ('Salvador', 'BA')."""
    if " - " in nome_completo:
        partes = nome_completo.rsplit(" - ", 1)
        return partes[0].strip(), partes[1].strip()[:2].upper()
    return nome_completo.strip(), "BA"


def transformar_indicadores_ibge() -> Path:
    """Lê o JSON bruto do IBGE, padroniza, valida e salva em CSV processado."""
    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Arquivo bruto não encontrado em {RAW_FILE}. Execute o passo 1.1 antes."
        )

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        coletas = json.load(f)

    registros = []

    for coleta in coletas:
        codigo_indicador = coleta["codigo_indicador"]
        fonte_id = coleta["fonte_id"]

        for variavel in coleta.get("resposta_api", []):
            nome_indicador = variavel.get("variavel", codigo_indicador).strip()
            unidade = variavel.get("unidade", "unidade").strip()

            for resultado in variavel.get("resultados", []):
                for item_serie in resultado.get("series", []):
                    localidade = item_serie.get("localidade", {})
                    codigo_ibge = str(localidade.get("id", "")).strip().zfill(7)
                    nome_loc = localidade.get("nome", "Salvador - BA")
                    municipio_nome, uf = separar_municipio_uf(nome_loc)

                    serie_historica = item_serie.get("serie", {})
                    for ano_str, valor_str in serie_historica.items():
                        if valor_str in VALORES_NULOS_IBGE:
                            continue

                        registros.append(
                            {
                                "codigo_ibge": codigo_ibge,
                                "municipio_nome": municipio_nome,
                                "uf": uf,
                                "codigo_indicador": codigo_indicador,
                                "nome_indicador": nome_indicador,
                                "unidade": unidade,
                                "ano_referencia": int(ano_str),
                                "valor": float(valor_str),
                                "fonte_id": int(fonte_id),
                            }
                        )

    df = pd.DataFrame(registros)

    if df.empty:
        raise ValueError("Nenhum registro válido foi extraído do JSON bruto.")

    # 1. Padronização do código IBGE para string de 7 dígitos
    df["codigo_ibge"] = df["codigo_ibge"].astype(str).str.zfill(7)

    # 2. Validações de integridade (compatíveis com as constraints do PostgreSQL)
    mask_ibge_valido = df["codigo_ibge"].str.match(r"^\d{7}$")
    mask_ano_valido = df["ano_referencia"].between(1900, 2100)
    mask_valor_valido = df["valor"].notna()

    df_valido = df[mask_ibge_valido & mask_ano_valido & mask_valor_valido].copy()

    # 3. Remoção de eventuais duplicatas na chave única do banco
    df_valido = df_valido.drop_duplicates(
        subset=["codigo_ibge", "codigo_indicador", "ano_referencia"],
        keep="last",
    ).sort_values(["codigo_indicador", "ano_referencia"])

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_valido.to_csv(PROCESSED_FILE, index=False, encoding="utf-8")

    print(f"[TRANSFORM] {len(df_valido)} observações validadas com sucesso!")
    print(f"[TRANSFORM] Arquivo processado salvo em: {PROCESSED_FILE}")
    print("\nPrévia dos dados tratados:")
    print(
        df_valido[
            ["codigo_ibge", "codigo_indicador", "ano_referencia", "valor", "unidade"]
        ].to_string(index=False)
    )

    return PROCESSED_FILE


if __name__ == "__main__":
    transformar_indicadores_ibge()
