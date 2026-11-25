# Transformações e reconciliação

O tratamento usa as nove tabelas do lote bruto e as validações do contrato. A trilha de injeção e o relatório de diagnóstico ficam disponíveis para conferência. O tratamento parte diretamente dos CSVs e registra seus hashes no manifesto.

| Ordem | Regra | Resultado |
| --- | --- | --- |
| 1 | Cópia exata de uma linha bruta | A primeira ocorrência segue para validação. As cópias são excluídas e têm seu ordinal registrado |
| 2 | Espaços nas extremidades | Remove os espaços e registra o valor de origem e o valor padronizado |
| 3 | Variante conhecida de segmento | Converte VAREJO, atac., Alimentacao e Servicos em Varejo, Atacado, Alimentação e Serviços, respectivamente |
| 4 | Chaves e campos únicos repetidos | Todas as versões remanescentes de uma chave primária conflitante, SKU repetido ou nome de categoria repetido vão à quarentena |
| 5 | Campo inválido ou obrigatório ausente | Aplica as validações de código, data, competência, domínio, valores inteiros, localidade e deduções. Sem correção determinística, preserva a linha original em quarentena |
| 6 | Referência inválida ou rejeitada | Coloca em quarentena o registro dependente e propaga a rejeição de cadastros para os pedidos, itens ou despesas que os referenciam |
| 7 | Pedido sem itens válidos | Coloca o pedido em quarentena. Pedidos com parte dos itens rejeitados permanecem utilizáveis pelos itens aceitos e aparecem no relatório de cobertura |

As datas aceitas preservam o formato ISO do contrato. Campos opcionais de localidade podem permanecer vazios em conjunto. A quarentena preserva os campos tal como foram lidos do CSV bruto e acrescenta o ordinal lógico (primeiro registro após o cabeçalho começa em 1). A trilha pode conter vários eventos do mesmo registro, inclusive ajustes seguidos de rejeição.

Cada linha bruta pertence a exatamente um destino: tratado, quarentena ou exclusão por duplicata exata. O manifesto compara esses destinos por tabela. Em itens e despesas, ele também compara os totais calculáveis em centavos e a quantidade de valores incalculáveis, separadamente por medida. Para o balanço bruto, espaços externos podem ser removidos antes de converter números e as fórmulas são aplicadas onde os campos necessários podem ser lidos. Os totais de quarentena e exclusão medem valores presentes nessas linhas e podem incluir cópias ou versões conflitantes. A trilha permite relacionar essas linhas às regras que as afetaram.

O relatório de cobertura indica pedidos parciais, pares de filial e mês sem despesas tratadas e o escopo de cada despesa rejeitada. Um mês ou uma filial nulos no escopo indicam que a perda pode afetar qualquer valor válido daquela dimensão. O módulo financeiro deve usar esse relatório para decidir se o resultado operacional pode ser exibido.

O lote de processamento é publicado de uma vez, com as pastas tratados, quarentena e relatorios em um destino novo. O manifesto inclui a versão das regras e os hashes dos arquivos publicados.