# Dicionário de dados — Orizon Sales

Versão do contrato: 1. Dados exclusivamente sintéticos.

## Convenções

- Cada tabela tem um arquivo CSV UTF-8 com cabeçalho, separador vírgula, aspas duplas e escape de aspas por duplicação. A ordem das colunas segue as tabelas abaixo. Gravação e leitura respeitam campos entre aspas.
- O formato canônico de data é AAAA-MM-DD. As competências usam uma data correspondente ao primeiro dia do mês. A janela de vendas inclui 2023-01-01 a 2025-12-31.
- Identificadores e códigos são textos, preservam zeros à esquerda e são validados como valores completos. Os prefixos dos identificadores são fixos por tabela. O sufixo contém dígitos e é gerado com zeros à esquerda: seis dígitos para itens e pedidos, cinco para as demais tabelas. O padrão do SKU é SKU- seguido por cinco dígitos. As chaves e o SKU são únicos em suas tabelas.
- Campos monetários terminados em _centavos contêm inteiros de 64 bits em centavos de real, sem separador ou símbolo. Quantidade também é um inteiro de 64 bits. Datas representam dias civis, sem fuso horário.
- Todos os campos são obrigatórios, salvo os indicados como opcionais. Um campo opcional vazio representa ausência. Espaços nas extremidades são removidos no tratamento, e um campo obrigatório vazio é inválido. A grafia canônica preserva acentos.
- As especificações abaixo descrevem a base válida. A base bruta preserva as mesmas colunas e pode conter dados que violem tipos ou regras. Na ingestão, os valores brutos são lidos como texto e validados antes da conversão.
- Os exemplos mostram o formato de cada valor. Prefixos e valores de exemplo são sintéticos.

## Cadastros

### clientes.csv

Uma linha por cliente. A geração prevê 5.000 clientes.

| Campo | Tipo | Restrição | Exemplo |
| --- | --- | --- | --- |
| cliente_id | texto | Chave primária, prefixo CLI- | CLI-00001 |
| nome_cliente | texto | Nome fictício | Mercado Horizonte |
| segmento | texto | Domínio gerado: Varejo, Atacado, Alimentação ou Serviços | Varejo |
| municipio | texto | Município fictício ou nome geográfico de referência, opcional | Fortaleza |
| uf | texto | Sigla de UF brasileira, opcional em conjunto com município | CE |
| data_cadastro | data | Igual ou anterior à primeira compra, se houver | 2022-11-10 |

Município e UF devem estar preenchidos em conjunto ou ambos ausentes. O mesmo critério vale para fornecedores. Nomes de clientes, vendedores, fornecedores e filiais podem se repetir e não identificam registros.

### fornecedores.csv

Uma linha por fornecedor.

| Campo | Tipo | Restrição | Exemplo |
| --- | --- | --- | --- |
| fornecedor_id | texto | Chave primária, prefixo FOR- | FOR-00001 |
| nome_fornecedor | texto | Nome fictício | Fornecedor Exemplo |
| municipio | texto | Opcional | Recife |
| uf | texto | Sigla de UF brasileira, opcional em conjunto com município | PE |

### categorias.csv

Uma linha por categoria de produto.

| Campo | Tipo | Restrição | Exemplo |
| --- | --- | --- | --- |
| categoria_id | texto | Chave primária, prefixo CAT- | CAT-00001 |
| nome_categoria | texto | Rótulo canônico único | Mercearia |

### produtos.csv

Uma linha por produto. A geração prevê 500 produtos.

| Campo | Tipo | Restrição | Exemplo |
| --- | --- | --- | --- |
| produto_id | texto | Chave primária, prefixo PRO- | PRO-00001 |
| sku | texto | Código comercial único | SKU-00001 |
| nome_produto | texto | Descrição fictícia | Café torrado 500 g |
| categoria_id | texto | Chave estrangeira para categorias | CAT-00001 |
| fornecedor_id | texto | Chave estrangeira para fornecedores | FOR-00001 |

### filiais.csv

Uma linha por filial. A geração prevê 5 filiais.

| Campo | Tipo | Restrição | Exemplo |
| --- | --- | --- | --- |
| filial_id | texto | Chave primária, prefixo FIL- | FIL-00001 |
| nome_filial | texto | Nome fictício | Filial Litoral |
| municipio | texto | Município da unidade | Fortaleza |
| uf | texto | Sigla de UF brasileira | CE |

### vendedores.csv

Uma linha por vendedor. A geração prevê 30 vendedores.

| Campo | Tipo | Restrição | Exemplo |
| --- | --- | --- | --- |
| vendedor_id | texto | Chave primária, prefixo VEN- | VEN-00001 |
| nome_vendedor | texto | Nome fictício | Helena Exemplo |
| filial_lotacao_id | texto | Chave estrangeira para filiais | FIL-00001 |

## Transações

### pedidos.csv

Uma linha por pedido. A data, o cliente, a filial efetiva e o vendedor identificam o contexto de todos os itens do pedido.

| Campo | Tipo | Restrição | Exemplo |
| --- | --- | --- | --- |
| pedido_id | texto | Chave primária, prefixo PED- | PED-000001 |
| data_venda | data | Dentro da janela e igual ou posterior ao cadastro do cliente | 2025-04-12 |
| cliente_id | texto | Chave estrangeira para clientes | CLI-00001 |
| filial_id | texto | Chave estrangeira para filiais, registra a unidade que realizou a venda | FIL-00002 |
| vendedor_id | texto | Chave estrangeira para vendedores | VEN-00001 |

Um vendedor pode vender por uma filial diferente da sua lotação. O desempenho por filial utiliza a filial do pedido. Cada pedido válido tem pelo menos um item válido. Se todos os itens forem rejeitados, o pedido segue para a quarentena com motivo próprio. Pedidos parcialmente tratados entram nos indicadores pelos itens aceitos, com contagem própria no relatório de qualidade.

### itens_venda.csv

Uma linha por item de pedido. A geração prevê 100.000 itens antes da injeção de defeitos. Um mesmo produto pode aparecer em linhas distintas do mesmo pedido, identificadas pelo item_id.

| Campo | Tipo | Restrição | Exemplo |
| --- | --- | --- | --- |
| item_id | texto | Chave primária, prefixo ITM- | ITM-000001 |
| pedido_id | texto | Chave estrangeira para pedidos | PED-000001 |
| produto_id | texto | Chave estrangeira para produtos | PRO-00001 |
| quantidade | inteiro | Maior que zero | 2 |
| preco_unitario_centavos | inteiro | Maior ou igual a zero | 1500 |
| desconto_centavos | inteiro | Total da linha, maior ou igual a zero | 200 |
| tributo_centavos | inteiro | Total da linha, maior ou igual a zero | 140 |
| custo_unitario_centavos | inteiro | Custo histórico por unidade, maior ou igual a zero | 850 |

A soma do desconto e do tributo deve ser menor ou igual ao bruto da linha. A geração arredonda desconto e tributo ao centavo mais próximo, com empate para cima. No exemplo, os valores em centavos são 3000 de faturamento bruto, 2660 de faturamento líquido, 1700 de custo da mercadoria e 960 de lucro bruto.

### despesas.csv

Uma linha por lançamento de despesa. Uma filial pode ter vários lançamentos de um mesmo tipo no mês.

| Campo | Tipo | Restrição | Exemplo |
| --- | --- | --- | --- |
| despesa_id | texto | Chave primária, prefixo DES- | DES-00001 |
| mes_competencia | data | Primeiro dia de um mês existente na janela | 2025-04-01 |
| filial_id | texto | Chave estrangeira para filiais | FIL-00002 |
| tipo_despesa | texto | Domínio gerado: Pessoal, Aluguel, Logística, Utilidades ou Administração | Logística |
| valor_centavos | inteiro | Maior que zero | 250000 |

As despesas são agregadas por filial e mês antes da comparação com o lucro bruto. Associar diretamente lançamentos aos itens multiplicaria seus valores. O gerador garante cobertura de despesas em todos os pares de filial e mês. Caso o tratamento deixe um par sem lançamentos confiáveis ou identifique perda de valor para o mês e a filial, o resultado operacional correspondente deve aparecer como indisponível. Se um lançamento perdido não puder ser atribuído a um mês e filial, a indisponibilidade abrange os recortes cujo resultado pode ser afetado.

## Cardinalidades e validações entre tabelas

| Origem | Destino | Regra |
| --- | --- | --- |
| Categorias e fornecedores | Produtos | Cada produto tem uma categoria e um fornecedor. Cada cadastro pode aparecer em zero ou mais produtos |
| Filiais | Vendedores | Cada vendedor tem uma filial de lotação. Cada filial pode ter zero ou mais vendedores |
| Clientes, filiais e vendedores | Pedidos | Cada pedido referencia exatamente um cadastro de cada entidade. Cada cadastro pode aparecer em zero ou mais pedidos |
| Pedidos | Itens de venda | Cada pedido tratado tem um ou mais itens. Cada item tem exatamente um pedido |
| Produtos | Itens de venda | Cada item tem um produto. Cada produto pode aparecer em zero ou mais itens |
| Filiais | Despesas | Cada despesa tem uma filial. Uma filial tem zero ou mais despesas no conjunto tratado |

O vínculo entre cliente e data da venda é validado após a resolução das referências. Registros com chaves estrangeiras inválidas vão à quarentena, inclusive quando a referência aponta para um cadastro rejeitado.

## Metadados de qualidade

O manifesto da execução registra versão do contrato, versões das regras e do gerador, sementes, janela, arquivos, hashes SHA-256 e contagens por tabela antes da injeção, na entrada bruta e na saída tratada. A trilha de qualidade guarda o arquivo de origem, o número ordinal do registro lógico após o cabeçalho, a chave original quando disponível, a regra, o campo afetado, o destino e o impacto financeiro quando calculável. Usar o ordinal permite rastrear duplicatas e registros sem chave. A quarentena preserva os valores brutos e vincula cada registro às regras que motivaram sua rejeição. O registro de defeitos injetados fica separado dos resultados do diagnóstico.