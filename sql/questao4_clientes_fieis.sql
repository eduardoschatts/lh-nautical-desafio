-- Questão 4: Top 10 clientes fiéis por Ticket Médio (mínimo de 13 categorias distintas)
-- Premissa: Todas as transações consideradas, seguindo a definição literal do enunciado ("contagem total de transações")

-- Etapa 1: Faturamento, frequência e ticket médio por cliente (AVG equivale a SUM/COUNT, pois cada linha de orders é uma transação)
WITH metricas_cliente as (
    SELECT
        customer_id,
        SUM(total) as faturamento_total,
        COUNT(*) as frequencia,
        AVG(total) as ticket_medio
    FROM orders
    GROUP BY customer_id
),

-- Etapa 2: Diversidade de categorias por cliente, percorrendo a cadeia orders -> order_items -> product_variants -> products
-- O DISTINCT evita contar a mesma categoria repetida a cada item comprado
diversidade_cliente as (
    SELECT
        o.customer_id,
        COUNT(DISTINCT p.category_id) as qtd_categorias
    FROM orders o
    JOIN order_items oi
        ON oi.order_id = o.id
    JOIN product_variants pv
        ON pv.id = oi.product_variant_id
    JOIN products p
        ON p.id = pv.product_id
    GROUP BY o.customer_id
),

-- Etapa 3: Filtro dos top 10 clientes (13+ categorias), ranking por ticket médio e desempate por customer_id crescente
top10_clientes_fieis as (
    SELECT
        m.customer_id,
        m.faturamento_total,
        m.frequencia,
        m.ticket_medio,
        d.qtd_categorias
    FROM metricas_cliente m
    JOIN diversidade_cliente d
        ON d.customer_id = m.customer_id
    WHERE d.qtd_categorias >= 13
    ORDER BY m.ticket_medio DESC, m.customer_id ASC
    LIMIT 10
)
SELECT * FROM top10_clientes_fieis;


-- Tarefa 3: Categoria com maior quantidade de itens (SUM(quantity)) comprados pelo grupo dos 10
-- As CTEs se repetem porque um WITH alimenta apenas um SELECT, assim cada comando roda isolado
WITH metricas_cliente as (
    SELECT
        customer_id,
        AVG(total) as ticket_medio
    FROM orders
    GROUP BY customer_id
),

diversidade_cliente as (
    SELECT
        o.customer_id,
        COUNT(DISTINCT p.category_id) as qtd_categorias
    FROM orders o
    JOIN order_items oi
        ON oi.order_id = o.id
    JOIN product_variants pv
        ON pv.id = oi.product_variant_id
    JOIN products p
        ON p.id = pv.product_id
    GROUP BY o.customer_id
),

top10_clientes_fieis as (
    SELECT m.customer_id
    FROM metricas_cliente m
    JOIN diversidade_cliente d
        ON d.customer_id = m.customer_id
    WHERE d.qtd_categorias >= 13
    ORDER BY m.ticket_medio DESC, m.customer_id ASC
    LIMIT 10
)

-- O JOIN com categories busca o nome da categoria; o WHERE customer_id IN garante que a soma reflete apenas os 10 do ranking
SELECT
    c.name as categoria,
    SUM(oi.quantity) as total_itens
FROM orders o
JOIN order_items oi
    ON oi.order_id = o.id
JOIN product_variants pv
    ON pv.id = oi.product_variant_id
JOIN products p
    ON p.id = pv.product_id
JOIN categories c
    ON c.id = p.category_id
WHERE o.customer_id IN (SELECT customer_id FROM top10_clientes_fieis)
GROUP BY c.name
ORDER BY total_itens DESC;


-- Análise de sensibilidade: o ranking muda quando colocamos os filtros:
-- Sem filtro:       22, 1477, 929, 1116, 1691, 774, 1470, 1599, 965, 1722
-- paid + confirmed: 300, 22, 1477, 1527, 1470, 1691, 1784, 1722, 965, 21
-- Só paid:          1527, 1581, 1558, 262, 22, 1470, 1113, 1301, 1116, 1814
-- Em cenário real, eu buscaria ativamente ir atrás da informação
-- A categoria campeã também muda: Hélices (492) sem filtro, Pesca (344) com paid+confirmed
-- Abaixo, a versão com filtro de pedidos efetivados (paid + confirmed) fica registrada para referência

-- WITH metricas_cliente as (
--     SELECT
--         customer_id,
--         SUM(total) as faturamento_total,
--         COUNT(*) as frequencia,
--         AVG(total) as ticket_medio
--     FROM orders
--     WHERE status IN ('paid','confirmed')
--     GROUP BY customer_id
-- ),
--
-- diversidade_cliente as (
--     SELECT
--         o.customer_id,
--         COUNT(DISTINCT p.category_id) as qtd_categorias
--     FROM orders o
--     JOIN order_items oi
--         ON oi.order_id = o.id
--     JOIN product_variants pv
--         ON pv.id = oi.product_variant_id
--     JOIN products p
--         ON p.id = pv.product_id
--     WHERE o.status IN ('paid','confirmed')
--     GROUP BY o.customer_id
-- ),
--
-- top10_clientes_fieis as (
--     SELECT
--         m.customer_id,
--         m.faturamento_total,
--         m.frequencia,
--         m.ticket_medio,
--         d.qtd_categorias
--     FROM metricas_cliente m
--     JOIN diversidade_cliente d
--         ON d.customer_id = m.customer_id
--     WHERE d.qtd_categorias >= 13
--     ORDER BY m.ticket_medio DESC, m.customer_id ASC
--     LIMIT 10
-- )
-- SELECT * FROM top10_clientes_fieis;