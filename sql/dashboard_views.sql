-- Modelo dimensional para o Power BI
-- Camada de consumo sobre as tabelas brutas carregadas na Questão 3
-- Padrão estrela: uma fato de vendas e quatro dimensões
 
 
-- Fato de vendas no grão de item de pedido
-- A margem usa unit_price (preço efetivamente cobrado, já com desconto) menos cost_price,
-- o que faz o prejuízo aparecer onde o desconto passou do custo
CREATE OR REPLACE VIEW vw_fato_vendas AS
SELECT
    oi.id as item_id,
    o.id as order_id,
    o.customer_id,
    o.location_id,
    o.salesperson_id,
    p.id as product_id,
    p.category_id,
    p.brand_id,
    o.created_at::date as data,
    o.channel,
    o.status,
    oi.quantity,
    oi.unit_price,
    pv.cost_price,
    oi.line_total as receita,
    pv.cost_price * oi.quantity as custo,
    (oi.unit_price - pv.cost_price) * oi.quantity as margem
FROM orders o
JOIN order_items oi
    ON oi.order_id = o.id
JOIN product_variants pv
    ON pv.id = oi.product_variant_id
JOIN products p
    ON p.id = pv.product_id;
 
 
-- Dimensão de produtos, já com categoria e marca resolvidas
-- A flag cadastro_valido marca os produtos cujo nome foge do padrão da base,
-- onde todo item legítimo termina com um número identificador
CREATE OR REPLACE VIEW vw_dim_produtos AS
SELECT
    p.id as product_id,
    p.name as produto,
    c.name as categoria,
    b.name as marca,
    p.unit_of_measure as unidade,
    p.is_active as ativo,
    (p.name ~ '[0-9]$') as cadastro_valido
FROM products p
LEFT JOIN categories c
    ON c.id = p.category_id
LEFT JOIN brands b
    ON b.id = p.brand_id;
 
 
-- Dimensão de clientes com o endereço principal
-- DISTINCT ON pega uma linha por cliente, priorizando o endereço marcado como primary
CREATE OR REPLACE VIEW vw_dim_clientes AS
SELECT DISTINCT ON (cu.id)
    cu.id as customer_id,
    cu.legal_name as cliente,
    cu.trade_name as nome_fantasia,
    cu.person_type as tipo_pessoa,
    cu.is_active as ativo,
    a.city as cidade,
    a.state as uf
FROM customers cu
LEFT JOIN addresses a
    ON a.customer_id = cu.id
ORDER BY cu.id, a.is_primary DESC NULLS LAST;
 
 
-- Dimensão de locais (lojas e armazéns)
CREATE OR REPLACE VIEW vw_dim_locais AS
SELECT
    l.id as location_id,
    l.name as local,
    l.location_type as tipo,
    l.city as cidade,
    l.state as uf,
    l.is_active as ativo
FROM locations l;
 
 
-- Dimensão de calendário, reaproveitando a lógica da Questão 5
-- Cobre todos os dias entre a menor e a maior data de venda, inclusive os sem movimento
CREATE OR REPLACE VIEW vw_dim_calendario AS
WITH periodo as (
    SELECT
        MIN(created_at)::date as data_inicio,
        MAX(created_at)::date as data_fim
    FROM orders
)
SELECT
    d::date as data,
    EXTRACT(year FROM d) as ano,
    EXTRACT(month FROM d) as mes,
    EXTRACT(day FROM d) as dia,
    DATE_TRUNC('month', d)::date as primeiro_dia_mes,
    EXTRACT(DOW FROM d) as num_dia_semana,
    CASE EXTRACT(DOW FROM d)
        WHEN 0 THEN 'Domingo'
        WHEN 1 THEN 'Segunda-feira'
        WHEN 2 THEN 'Terça-feira'
        WHEN 3 THEN 'Quarta-feira'
        WHEN 4 THEN 'Quinta-feira'
        WHEN 5 THEN 'Sexta-feira'
        WHEN 6 THEN 'Sábado'
    END as dia_semana,
    CASE EXTRACT(month FROM d)
        WHEN 1 THEN 'Jan' WHEN 2 THEN 'Fev' WHEN 3 THEN 'Mar'
        WHEN 4 THEN 'Abr' WHEN 5 THEN 'Mai' WHEN 6 THEN 'Jun'
        WHEN 7 THEN 'Jul' WHEN 8 THEN 'Ago' WHEN 9 THEN 'Set'
        WHEN 10 THEN 'Out' WHEN 11 THEN 'Nov' WHEN 12 THEN 'Dez'
    END as mes_nome,
    EXTRACT(DOW FROM d) IN (0, 6) as fim_de_semana
FROM periodo, generate_series(data_inicio, data_fim, '1 day'::interval) d;
 
 
-- Vendas diárias das lojas físicas com os dias zerados preservados (Questão 5)
-- O LEFT JOIN e o COALESCE são o que impedem a média por dia da semana de inflar
CREATE OR REPLACE VIEW vw_vendas_diarias_pos AS
WITH vendas as (
    SELECT
        created_at::date as data,
        SUM(total) as valor_vendas
    FROM orders
    WHERE channel = 'pos'
    GROUP BY created_at::date
)
SELECT
    cal.data,
    cal.num_dia_semana,
    cal.dia_semana,
    COALESCE(v.valor_vendas, 0) as vendas_dia,
    (v.valor_vendas IS NULL) as dia_sem_venda
FROM vw_dim_calendario cal
LEFT JOIN vendas v
    ON v.data = cal.data;