from typing import Dict, Any
from backtest.interfaces import Strategy, Portfolio, StrategyState


class MyStrategy:
    def initialize(self) -> StrategyState:
        # Setup the strategy parameters and initial state
        initial_state = {"example_parameter": 0}
        return StrategyState(state=initial_state)

    def on_data(self, data: Dict[str, Any], portfolio: Portfolio, state: StrategyState) -> StrategyState:
        # Define strategy logic, e.g., buy 10 shares of 'AAPL' if cash allows
        symbol = 'AAPL'
        price = data[symbol]['price']
        if portfolio.cash >= 10 * price:
            portfolio.cash -= 10 * price
            portfolio.positions[symbol] = portfolio.positions.get(
                symbol, 0) + 10
            portfolio.history.append(
                {"date": data['date'], "symbol": symbol, "quantity": 10, "price": price})

        # Update strategy state
        state.state["example_parameter"] += 1
        return state


if __name__ == "__main__":
    from backtest.framework import run_backtest
    import json
    from pathlib import Path

    # Example market data loading
    market_data_path = Path("path/to/market_data.json")
    market_data = json.loads(market_data_path.read_text())

    strategy = MyStrategy()
    run_backtest(strategy, market_data)
