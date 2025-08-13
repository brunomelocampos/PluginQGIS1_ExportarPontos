Plugin usado no QGIS para exportar TXT de pontos em formato adequado para entrada em equipamentos de GPS
Cada linha do arquivo (A partir da linha 2) contém os seguintes campos separados por tabulação (`TAB`):

Nome Descrição X Y Z ou 
Nome Descrição Y X Z

> Exemplo:
> `Ponto A[TAB]Cerca[TAB]500000.123[TAB]7500000.456[TAB]100.000`

As colunas `Nome`, `Descrição` e `Z` são opcionais e só aparecem se forem selecionadas na interface.

A fonte de `Z` é confugurável assim como separador decimal("." ou ",") e arredondamento com casas decimais.
