# Trade Burner Terminal V1

Modular foundation for Trade Burner. The current working pure option-chain engine is preserved under `engine/option_chain_engine.py`.

## Run
1. Create/activate your Python environment.
2. `pip install -r requirements.txt`
3. Set `DHAN_ACCESS_TOKEN` in the environment.
4. `streamlit run app.py`

V1 includes Dashboard/Index Options shell, live Dhan option-chain fetch, current option-chain analysis, entry-wait setup display, and placeholders for scanner/strategies/risk/journal modules.
