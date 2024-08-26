from quantanalyzer.interfaces import Strategy, Portfolio, DataProvider, SymbolValues

from datetime import datetime, timedelta
import pandas as pd


def _comp_transactions(planned_position: SymbolValues, current_position_percentages: SymbolValues) -> SymbolValues:
    # Verifica a diferença entre a posição planejada e a posição atual
    percentages_delta: SymbolValues = {symbol: planned_position.get(symbol, 0.0) - current_position_percentages.positions.get(symbol, 0.0)
                                       for symbol in set(planned_position.keys()) | set(current_position_percentages.keys())}

    # Filtra apenas as posições que possuem diferença
    percentages_delta = {symbol: delta for symbol,
                         delta in percentages_delta.items() if delta != 0.0}

    return percentages_delta


def run_backtest(strategy: Strategy, data_provider: DataProvider,
                 start_date: datetime, end_date: datetime | None = None,
                 initial_portfolio: Portfolio | None = None, freq: str | timedelta = 'B') -> None:

    # Inicializa o portfólio
    if initial_portfolio is None:
        initial_portfolio = Portfolio()
        initial_portfolio.positions['CASH'] = 10_000_000.0
    portfolio = initial_portfolio

    # Define end_date como a data atual caso não seja fornecida
    if end_date is None:
        # Normaliza para o primeiro horário do dia
        end_date = pd.Timestamp.now().normalize()

    # Realiza o backtest iterativo de start_date até end_date
    for today in pd.date_range(start_date, end_date, freq=freq):

        # Computa a estratégia para a iteração atual
        planned_position = strategy.compute(today, portfolio)

        # Recupera a posição atual em percentuais
        current_position_percentages = portfolio.get_position_in_percentages()

        # Calcula as transações necessárias em percentuais
        percentages_delta: SymbolValues = _comp_transactions(
            planned_position, current_position_percentages)

        # Calcula os custos percentuais de transação
        #
        # Enviar tanto a posição anterior como a nova para verificar início ou término de uma posição
        #
        #
        #
        #

        # Computa o dicionário com as transações necessárias, i.e., a quantidade em moeda de referência (CASH) a ser comprada ou vendida
        current_position_value = portfolio.get_position_value(
            data_provider, today)
        transactions: SymbolValues = {symbol: current_position_value * percentage for symbol,
                                      percentage in set(percentages_delta.keys()) if percentage != 0.0}

        # Simula a realização das transações caso exista oferta (de compra/venda)
        quote_delta: SymbolValues = {}
        transaction_costs: SymbolValues = {}

        for symbol, amount in transactions.items():
            book = data_provider.get_book(symbol, today)

            if amount > 0:
                # Compra
                price = book[0]  # ask: melhor preço de venda
            elif amount < 0:
                # Venda
                price = book[1]  # bid: melhor preço de compra

            quantity = amount / price
            quote_delta[symbol] += quantity

    # Output final portfolio and transaction history
    print("Final Portfolio:", portfolio.positions)
