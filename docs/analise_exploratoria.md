# Análise exploratória — Orizon Sales

Base tratada de 01/01/2023 a 31/12/2025, com 36 meses observados.

## Perfil comercial

- 98.694 itens em 46.992 pedidos e 4.700 clientes ativos.
- Média de 10,00 pedidos por cliente ativo, com 485 clientes que compraram uma vez.
- Ticket médio de R$ 2.265,53, mediana de R$ 1.984,21 e percentil 90 de R$ 4.557,99.
- Filial Fortaleza · FIL-00001 liderou as vendas, com R$ 31.594.388,02 de faturamento líquido.

## Receita e rentabilidade

- Faturamento bruto de R$ 121.539.366,95 e líquido de R$ 106.461.920,09. Lucro bruto de R$ 27.842.621,25 e margem de 26,2%.
- A classe A reúne 169 de 500 produtos vendidos e responde por 80,1% da receita líquida.
- 4 recortes de filial e competência têm despesas rejeitadas. Por isso, o resultado operacional do período integral fica indisponível.

## Evolução e sazonalidade

- 12/2025 registrou a maior receita líquida mensal. O último mês da janela variou 7,5% ante o mês anterior e 10,0% ante o mesmo mês do ano anterior.
- O mês-calendário 12 apresentou a maior média e o mês 02, a menor. Cada mês-calendário teve três observações completas.
- A correlação descritiva de Spearman entre receita líquida e número de pedidos nos 36 meses foi 0,953 (SciPy).

## Limitações

- 751 pedidos permaneceram com apenas os itens aceitos. Os indicadores comerciais usam os valores desses itens.
- O gerador incorpora sazonalidade de volume, diferenças entre filiais e reajustes anuais. Os padrões encontrados descrevem esse cenário sintético.
