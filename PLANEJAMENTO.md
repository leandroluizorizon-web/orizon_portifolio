# Orizon Sales — Planejamento para aprovação

A pasta D:/orizon/projetos/portifolio está vazia no início desta etapa e ainda não é um repositório Git. O projeto será estruturado diretamente nela.

## Arquitetura proposta

1. **Geração** — Faker em pt_BR para cadastros fictícios e NumPy para simular volumes, preços, custos, carteiras, sazonalidade e diferenças entre filiais. Uma etapa separada injeta defeitos com semente própria.
2. **Pipeline** — Arquivos CSV UTF-8 como entrada bruta. Pandas valida, diagnostica, trata e exporta tabelas padronizadas e relatórios. A publicação do conjunto tratado ocorre após as validações, com manifesto para identificar a execução.
3. **Análise** — Funções Python independentes do Streamlit centralizam filtros, agregações e indicadores. Pandas e NumPy atendem às análises descritivas. SciPy será usado na exploração quando houver uma medida descritiva apropriada, como correlação de Spearman entre séries mensais.
4. **Interface** — Streamlit com gráficos Plotly, navegação por módulo, filtros compartilhados e cache por versão dos dados tratados. Cards, séries temporais, rankings e tabelas adaptam-se a telas menores. A demonstração lê artefatos tratados gerados previamente e funciona sem banco externo ou serviço pago.

```text
portifolio/
├── AGENTS.md
├── PLANEJAMENTO.md
├── README.md
├── app.py
├── pyproject.toml
├── requirements.txt
├── docs/
│   ├── dicionario_dados.md
│   └── transformacoes.md
├── dados/
│   ├── brutos/
│   ├── relatorios/
│   └── processamento/<lote>/
│       ├── tratados/
│       ├── quarentena/
│       └── relatorios/
├── src/orizon_sales/
│   ├── geracao/
│   ├── qualidade/
│   ├── tratamento/
│   ├── analise/
│   └── visualizacao/
└── tests/
```

## Modelo de dados proposto

| Tabela | Granularidade e chave | Campos centrais e vínculos |
| --- | --- | --- |
| clientes | Um cliente por cliente_id | Nome fictício, segmento, município, UF, data de cadastro |
| fornecedores | Um fornecedor por fornecedor_id | Nome fictício, município, UF |
| categorias | Uma categoria por categoria_id | Nome da categoria |
| produtos | Um produto por produto_id | SKU único, nome, categoria_id e fornecedor_id |
| filiais | Uma filial por filial_id | Nome fictício, município, UF |
| vendedores | Um vendedor por vendedor_id | Nome fictício, filial de lotação; os pedidos guardam a filial efetiva da venda |
| pedidos | Um pedido por pedido_id | Data da venda, cliente_id, filial_id e vendedor_id |
| itens_venda | Uma linha por item_id | pedido_id, produto_id, quantidade, preço unitário, desconto total da linha, tributo total da linha e custo unitário histórico |
| despesas | Um lançamento por despesa_id | Mês de competência, filial_id, tipo de despesa e valor |

Pedidos têm um ou mais itens. Clientes, vendedores e filiais têm relação de um para muitos com pedidos. Categorias e fornecedores têm relação de um para muitos com produtos. Filiais também têm relação de um para muitos com despesas. Canais, devoluções e cancelamentos ficam fora do escopo proposto para esta primeira demonstração.

A simulação parte de **100.000 itens válidos antes da injeção de defeitos**, distribuídos em pedidos ao longo de **36 meses completos**, com **5.000 clientes, 500 produtos, 5 filiais e 30 vendedores**, além de fornecedores, categorias e despesas. A janela inicial proposta é janeiro de 2023 a dezembro de 2025. Duplicatas adicionadas aumentam a contagem bruta e a quarentena pode reduzir a contagem tratada. O manifesto apresenta as três contagens.

## Regras de tratamento

- Injetar duplicatas exatas, duplicatas conflitantes, campos ausentes, datas inválidas ou fora da janela, rótulos cadastrais divergentes e formatos incorretos em medidas e códigos. Registrar a configuração e a quantidade de defeitos planejados por tipo.
- Diagnosticar completude, unicidade, formato, domínio, integridade referencial e diferenças entre fontes antes da limpeza. Os indicadores de qualidade são calculados a partir das validações, mantendo o registro da injeção separado para aferição.
- Padronizar espaços, formatos de data e numéricos conforme o contrato de entrada. Resolver variantes cadastrais por mapeamento documentado e inequívoco. Preservar a identificação original das linhas.
- Remover cópias exatas. Encaminhar duplicatas conflitantes, referências sem correspondência, datas inválidas e campos críticos sem recuperação determinística à quarentena. Um pedido rejeitado leva seus itens à quarentena. Campos opcionais ausentes recebem indicação de ausência na apresentação. Valores financeiros ausentes não viram zero.
- Registrar por regra o motivo, a contagem de registros, o destino e o impacto financeiro quando calculável. Reconciliar entradas, saídas, exclusões e quarentena por tabela. Aplicar as mesmas regras em reexecuções sobre a mesma entrada.

## Regras dos indicadores

| Indicador | Definição proposta |
| --- | --- |
| Faturamento bruto | Soma de quantidade × preço unitário |
| Faturamento líquido | Faturamento bruto menos descontos e tributos sobre vendas |
| Lucro bruto | Faturamento líquido menos custo da mercadoria vendida, calculado com o custo unitário histórico de cada item |
| Margem bruta | Lucro bruto dividido pelo faturamento líquido |
| Resultado operacional gerencial | Lucro bruto menos despesas por competência, com recorte de mês completo e filial. Filtros por cliente, produto ou vendedor tornam o resultado indisponível, pois as despesas não têm esse detalhamento |
| Ticket médio | Faturamento líquido dividido pelo número de pedidos distintos com itens no recorte. Sob filtro de produto, mede o valor dos itens selecionados por pedido |
| Crescimento mensal e anual | Variação percentual do faturamento líquido diante do mês anterior e do mesmo mês do ano anterior. Para meses parciais, usar os mesmos dias nas referências quando houver cobertura equivalente. Bases ausentes ou iguais a zero exibem indisponibilidade |
| Curva ABC | Ordenar produtos por faturamento líquido decrescente, com desempate pelo SKU. Classificar pelo acumulado anterior ao item, com limites de 80% e 95%, mantendo o item que cruza cada limite na classe que ele completa. Exibir itens sem faturamento positivo separadamente |
| Sazonalidade | Perfil do faturamento líquido por mês do calendário, com média dos meses completos disponíveis e indicação da quantidade de observações de cada mês |
| Frequência de compra | Pedidos distintos por cliente no período. A média consolidada usa clientes com pelo menos um pedido no recorte |
| Rentabilidade por produto | Lucro bruto e margem bruta calculados por produto com custo histórico, sem rateio de despesas |
| Filiais e vendedores | Faturamento líquido, lucro bruto, margem, pedidos e ticket por filial efetiva e vendedor registrados no pedido |

Quantidade é inteira e positiva. Preços, descontos, tributos, custos e despesas usam centavos inteiros. Desconto e tributo são totais por linha e sua soma não pode exceder o valor bruto da linha. A geração arredonda descontos e tributos para o centavo mais próximo, com empate para cima. As agregações somam centavos e calculam percentuais sobre os totais. Denominadores iguais a zero exibem indicador indisponível.

## Plano de implementação

| Fase | Entrega e critério de conclusão |
| --- | --- |
| 1. Planejamento e arquitetura | Arquitetura, árvore de pastas, entidades, regras e cronograma aprovados pelo responsável pelo projeto |
| 2. Modelagem das tabelas | Esquemas e dicionário com tipos, chaves, cardinalidades, restrições, unidades e exemplos |
| 3. Geração dos dados fictícios | Gerador parametrizado, base bruta imutável, defeitos configuráveis e manifesto com sementes, período e contagens |
| 4. Diagnóstico da qualidade | Perfil por tabela e relatório de defeitos com exemplos, impacto e taxa por regra |
| 5. Limpeza e transformação | Dados tratados, quarentena e trilha de transformações, com reconciliação de registros e valores |
| 6. Análise exploratória | Perfil comercial e financeiro, sazonalidade, distribuições e registro das limitações da simulação |
| 7. Desenvolvimento dos indicadores | Funções independentes da interface, fórmulas documentadas e resultados reconciliados com exemplos de referência |
| 8. Desenvolvimento do dashboard | Oito módulos em Streamlit com filtros, cards, gráficos e tabelas. Verificação dos fluxos em desktop e tela menor |
| 9. Testes e revisão | Pytest para geração, pipeline e indicadores, teste de ponta a ponta e revisão visual dos oito módulos |
| 10. Documentação e publicação | README completo, dicionário e guia de demonstração. Validar o alvo gratuito e publicar no GitHub e na hospedagem após confirmação do destino |

Na fase 8, a **Visão executiva** reúne os indicadores centrais e a evolução mensal. **Desempenho comercial** compara períodos e mostra sazonalidade. **Análise financeira** detalha descontos, tributos, custos e despesas. **Análise de clientes** apresenta frequência, segmentos e ticket. **Desempenho dos produtos** reúne ABC e rentabilidade. **Comparação entre filiais** e **Desempenho dos vendedores** apresentam rankings e evolução com filtros coerentes. **Qualidade dos dados** mostra contagens de entrada, tratamento e quarentena, além do diagnóstico por regra.