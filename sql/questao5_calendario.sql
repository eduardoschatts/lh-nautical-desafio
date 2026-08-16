-- Questão 5: Média de vendas por dia da semana nas lojas físicas (pos)
-- Etapa 1: período coberto pelas vendas presenciais, extraído da própria base
WITH periodo as (
    SELECT
        MIN(created_at)::date as data_inicio,
        MAX(created_at)::date as data_fim
    FROM orders
    WHERE channel = 'pos'
),

-- Etapa 2: gera uma linha por dia dentro do período, incluindo dias sem venda
calendario as (
    SELECT
        generate_series(data_inicio, data_fim, '1 day'::interval)::date as data
    FROM periodo
),

-- Etapa 3: traduz o dia da semana para português
-- EXTRACT(DOW) numera de 0 (domingo) a 6 (sábado), num_dia é guardado para ordenação posterior
calendario_novo as (
    SELECT
        data,
        EXTRACT(DOW FROM data) as num_dia,
        CASE EXTRACT(DOW FROM data)
            WHEN 0 THEN 'Domingo'
            WHEN 1 THEN 'Segunda-feira'
            WHEN 2 THEN 'Terça-feira'
            WHEN 3 THEN 'Quarta-feira'
            WHEN 4 THEN 'Quinta-feira'
            WHEN 5 THEN 'Sexta-feira'
            WHEN 6 THEN 'Sábado'
        END as dia_semana
    FROM calendario
),

-- Etapa 4: soma das vendas por dia, apenas do canal presencial
-- O ::date corta a hora, senão cada pedido viraria um grupo diferente
vendas_diarias as (
    SELECT
        created_at::date as data,
        SUM(total) as valor_vendas
    FROM orders
    WHERE channel = 'pos'
    GROUP BY created_at::date
),

-- Etapa 5: LEFT JOIN preserva os dias sem venda, que o GROUP BY direto na tabela de vendas descartaria
-- COALESCE transforma o NULL em zero, pois AVG() ignora NULLs e a média voltaria a ficar inflada
vendas_por_dia as (
    SELECT
        c.data,
        c.num_dia,
        c.dia_semana,
        COALESCE(v.valor_vendas, 0) as vendas_dia
    FROM calendario_novo c
    LEFT JOIN vendas_diarias v
        ON v.data = c.data
)

-- Média por dia da semana considerando todos os dias do calendário
-- media_sem_calendario reproduz o erro do estagiário: ao ignorar os dias zerados e subindo a média ao diminuir o divisor
SELECT
    dia_semana,
    COUNT(*) as qtd_dias,
    COUNT(*) FILTER (WHERE vendas_dia = 0) as dias_sem_venda,
    AVG(vendas_dia) as media_correta,
    AVG(vendas_dia) FILTER (WHERE vendas_dia > 0) as media_sem_calendario
FROM vendas_por_dia
GROUP BY num_dia, dia_semana
ORDER BY media_correta ASC;
