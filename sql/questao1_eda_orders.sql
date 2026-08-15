-- Questão 1.1: Visão geral de ORDERS no período
select 
	COUNT(*) as total_linhas,
	MIN(created_at) as data_minima,
	MAX(created_at) as data_maxima,
	MIN(total) as valor_minimo,
	MAX(total) as valor_maximo,
	AVG(total) as valor_medio
from orders;

-- Quantidade de colunas em ORDERS
select 
    COUNT(*) as total_colunas
from information_schema.columns
where table_name = 'orders';


-- Questão 1.3: Distribuição de total em ORDERS (avaliação de outliers)
-- Comparando a média, mediana, percentis e desvio padrão para ver o grau de assimetria existente
SELECT
    MIN(total) AS valor_minimo,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY total) as valor_25_percentil,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total) as valor_mediana,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY total) as valor_75_percentil,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total) as valor_99_percentil,
    MAX(total) AS valor_maximo,
    AVG(total) AS valor_medio,
    STDDEV(total) AS desvio_padrao,
    STDDEV(total) / AVG(total) AS coef_variacao
FROM orders;

-- Apoiar na questão 1.3: Verificamos se campos possuem valores nulos que possam danificar a análise
SELECT 
    COUNT(*) filter (where customer_id is null) as customer_id_nulos,
    COUNT(*) filter (where salesperson_id is null) as salesperson_id_nulos,
    COUNT(*) filter (where location_id is null) as location_id_nulos,
    COUNT(*) filter (where total is null) as total_nulos,
    COUNT(*) filter (where created_at is null) as created_at_nulos
FROM orders;

-- Apoio à questão 1.3: Origem dos nulos do campo salesperson_id, vendo relacionado ao canal de origem
SELECT 
    channel,
    COUNT(*) as total_pedidos,
    COUNT(*) filter (where salesperson_id is null) as salesperson_id_nulos
FROM orders
GROUP BY channel
order by total_pedidos desc;

-- Apoio à questão 1.3: Verificar qual o andamento dos pedidos, se estão em aberto, cancelados ou finalizados e que eles estão sendo contabilizados na média
select
    status,
    COUNT(*) as pedidos,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) over (), 1) as percentual
from orders
group by status
order by pedidos desc;

-- Mede o quanto os pedidos não finalizados deslocam a média
select
    AVG(total) as media_todos_status,
    AVG(total) filter (where status in ('paid','confirmed')) as media_efetivados
from orders;

--- Apoio à questão 1.3: Visualizar a distribuição dos pedidos por ano
SELECT    
	EXTRACT(year from created_at) as ano,
    COUNT(*) as pedidos
FROM orders
GROUP BY ano
ORDER BY ano;