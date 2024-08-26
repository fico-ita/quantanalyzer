from typing import Protocol, Dict, List, Tuple
from datetime import datetime

# Tipo para definir um dicionário de símbolo com um tipo de valor associado:
# - str: Símbolo do ativo
# - float: Cotas, preço ou valor do ativo ou seu peso percentual no portfólio
SymbolValues = Dict[str, float]

# Tipo para registro do histórico dos valores de um símbolo:
# - datetime: Data da ocorrência
# - SymbolEntry: Estado do símbolo na data
SymbolsHistory = List[Tuple[datetime, SymbolValues]]

BidPrice = float
AskPrice = float


class CostPlan(Protocol):
    """
    Interface que define um plano de custos para transações de ativos.

    A implementação padrão é a do custo percentual cobrado pela B3 para swing trade de ações, mas você pode sobrescrever essa implementação ou detalhar por symbol. Veja a [Tabela de Tarifas B3](https://www.b3.com.br/pt_br/produtos-e-servicos/tarifas/listados-a-vista-e-derivativos/renda-variavel/tarifas-de-acoes-e-fundos-de-investimento/a-vista/).
    """

    def get_percentage_cost(self, symbol: str, amount: float, date: datetime) -> float:
        """Retorna o custo percentual de transação de um ativo em determinado tempo.
        Por exemplo, para uma transação de compra (0.5%) de um ativo e considerando um custo de 0.03%, temos que o valor final da transação será 0.5% / (1 - 0.03%) ~ 0.50015%. Assim o custo percentual da transação é 0.00015%.

        :param symbol: Símbolo do ativo.
        :param amount: Quantidade do ativo em percentuais a comprar (positivo) ou vender (negativo), e.g.: '-0.5%'.
        :param date: Data e tempo de referência da transação.
        :return: Custo percentual da transação do ativo, a ser adicionado na transação.
        """
        taxa_total = 0.00_03
        return amount * taxa_total / (1 - taxa_total)


class DataProvider(Protocol):
    """
    Interface que define um serviço de dados para obter as informações sobre os valores e ofertas dos ativos.

    Diferenciamos valor de oferta do book de ordens pelas respectivas funções `get_value` e `get_book`.

    Por padrão, assumimos que o valor do ativo é o preço de venda(ask) do ativo, mas você pode sobrescrever essa implementação.

    TODO: Incorporar a quantidade de ativos disponíveis para compra/venda(liquidez) no book de ordens.
    """

    def get_book(self, symbol: str, date: datetime) -> Tuple[BidPrice, AskPrice]:
        """Retorna a tupla de preços[bid, ask] de um ativo, em determinado tempo, na mesma moeda de referência do portfólio(CASH).

        : param symbol: Símbolo do ativo.
        : param date: Data e tempo de referência do preço.
        : return: Tupla de preços[bid, ask] do ativo.
        """
        pass

    def get_books(self, symbols: List[str], date: datetime) -> Dict[str, Tuple[BidPrice, AskPrice]]:
        """Retorna um dicionário com os preços[bid, ask] de vários ativos, em determinado tempo, na mesma moeda de referência do portfólio(CASH).

        : param symbols: Lista de símbolos dos ativos.
        : param date: Data e tempo de referência dos preços.
        : return: Dicionário de preços[bid, ask] dos ativos.
        """
        return {symbol: self.get_book(symbol, date) for symbol in symbols}

    def get_value(self, symbol: str, amount: float, date: datetime) -> float:
        """Retorna o valor de um ativo em determinado tempo, na mesma moeda de referência do portfólio(CASH).

        : param symbol: Símbolo do ativo.
        : param amount: Quantidade do ativo(cotas).
        : param date: Data e tempo de referência do preço.
        : return: Valor do ativo.
        """
        if amount > 0:
            # Comprado
            # Assume-se que o valor do ativo é o preço de venda (ask)
            return self.get_book(symbol, date)[1] * amount
        else:
            # Vendido
            # Assume-se que o valor do ativo é o preço de compra (bid)
            return self.get_book(symbol, date)[0] * amount

    def get_values(self, symbols: SymbolValues, date: datetime) -> SymbolValues:
        """Retorna um dicionário com os valores de vários ativos, em determinado tempo, na mesma moeda de referência do portfólio(CASH).

        : param symbols: Lista de símbolos dos ativos e suas respectivas cotas.
        : param date: Data e tempo de referência dos preços.
        : return: Dicionário de valores dos ativos.
        """
        return {symbol: self.get_value(symbol, amount, date) for symbol, amount in symbols}


class Portfolio(Protocol):
    """
    Classe que representa um portfólio de ativos.

    Atributos:
    - `position_quotes`: Dicionário com as posições do portfólio em termos de cotas. As chaves são os símbolos dos ativos(e.g., 'AAPL', 'PETR4') e os valores são as quantidades de cotas desses ativos.
      - `CASH`: Ativo especial para conter o montante em dinheiro(parado).
    - `hist_position_quotes`: Lista que armazena o histórico de cotas anteriores do portfólio.
    - `hist_cost`: Lista que armazena o histórico de custos de operações realizadas no portfólio. Cada item na lista é um dicionário contendo os custos de transação para cada ativo transacionado.
    """

    def __init__(self):
        self.position_quotes: SymbolValues = {}
        self.hist_position_quotes: SymbolsHistory = []
        self.history_cost: SymbolsHistory = []

    def get_position_in_percentages(self) -> SymbolValues:
        total = sum(self.position_quotes.values())
        return {symbol: amount / total for symbol, amount in self.position_quotes.items()}

    def get_position_value(self, data_provider: DataProvider, date: datetime) -> float:
        """
        Retorna o valor total do portfólio em determinado tempo, na mesma moeda de referência do portfólio(CASH).
        """
        return sum(data_provider.get_value(symbol, amount, date) for symbol, amount in self.position_quotes.items())

    # def trade_current_positions(self, date: datetime) -> None:
    #    self.history.append((date, self.positions))


class Strategy(Protocol):
    """
    Interface que define uma estratégia de investimento.

    Basta implementar o método `compute` que define a lógica da estratégia de investimento. Caso haja necessidade de inicialização, implemente o método `initialize`.

    Se sua estratégia necessite de um estado interno, você deve tratar isso na implementação da estratégia.
    """

    def initialize(self) -> None:
        pass

    def compute(self, today: datetime, portfolio: Portfolio) -> SymbolValues:
        """A lógica da estratégia deve ser apenas computar o próximo estado do portfólio com base no estado atual do portfólio, para que o backtest possa ser executado de forma iterativa
        A data atual da simulação(today) é fornecida para solicitar os dados(point-in -time) ao serviço de dados disponível.

        : param today: Data considerada hoje durante a simulação da iteração atual do backtest.
        : param portfolio: Estado atual e histórico do portfólio, caso desejar utilizá-lo na estratégia.
        : return: Próximo estado do portfólio em termos percentuais, e.g., {'AAPL': 0.1, 'PETR4': 0.2} para comprar 10 % de AAPL e 20 % de PETR4.
        """
        pass
