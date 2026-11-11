-- Habilitar recursos espaciais
CREATE EXTENSION IF NOT EXISTS postgis;

-- Camadas do banco
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Registro das fontes
CREATE TABLE IF NOT EXISTS raw.fontes (
    id BIGSERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    url TEXT,
    data_coleta TIMESTAMPTZ DEFAULT NOW()
);

-- Municípios
CREATE TABLE IF NOT EXISTS core.municipios (
    codigo_ibge VARCHAR(7) PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    uf CHAR(2) NOT NULL,
    geom geometry(MultiPolygon, 4674)
);

-- Indicadores
CREATE TABLE IF NOT EXISTS core.indicadores (
    id BIGSERIAL PRIMARY KEY,
    codigo_indicador VARCHAR(100) UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    unidade VARCHAR(50)
);

-- Valores observados
CREATE TABLE IF NOT EXISTS core.observacoes (
    id BIGSERIAL PRIMARY KEY,

    codigo_ibge VARCHAR(7) NOT NULL
        REFERENCES core.municipios(codigo_ibge),

    indicador_id BIGINT NOT NULL
        REFERENCES core.indicadores(id),

    ano_referencia INTEGER NOT NULL
        CHECK (ano_referencia BETWEEN 1900 AND 2100),

    valor NUMERIC,

    fonte_id BIGINT
        REFERENCES raw.fontes(id),

    UNIQUE (
        codigo_ibge,
        indicador_id,
        ano_referencia
    )
);

-- Índice espacial
CREATE INDEX IF NOT EXISTS idx_municipios_geom
ON core.municipios
USING GIST (geom);

-- Índice para consultas analíticas
CREATE INDEX IF NOT EXISTS idx_observacoes_ano
ON core.observacoes (ano_referencia);