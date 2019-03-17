## parser_edsl
Библиотека генератора LALR(1) парсеров на языке Python 3. Позволяет описывать грамматику языка с помощью удобного EDSL с возможностью указания семантических действий.

### Установка
Для представления упорядоченных множеств используется модуль `orderedset`:
```bash
pip install orderedset
```

### Как использовать
Необходимо выполнить следующие шаги:
* написать лексический анализатор, порождающий последовательность токенов (наследников библиотечного класса `Token`)
* описать грамматику и семантические действия с помощью EDSL
* вызвать метод `parse` с передачей входных данных у стартового нетерминала (аксиомы)

### Синтаксис описания правил
```
Нетерминал += Тег_или_Нетерминал << Тег_или_Нетерминал << (Замыкание с семантическим действием) | Альтернатива.
```

### Примеры 
Примеры использования библиотеки можно найти в папке `examples`.